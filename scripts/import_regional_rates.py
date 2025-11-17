"""
Data Import Scripts for Regional Tax Rates.

This script imports official Italian tax rates from various sources
including CSV files, government APIs, and manual data entry.
"""

import asyncio
import csv
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiohttp
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.regional_taxes import (
    DEFAULT_REGIONAL_DATA,
    DEFAULT_TAX_RATES,
    ComunalTaxRate,
    Comune,
    RegionalTaxRate,
    Regione,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RegionalTaxImporter:
    """
    Importer for Italian regional and municipal tax rates.

    Supports multiple data sources and formats for comprehensive
    tax rate database population.
    """

    def __init__(self, db_url: str = None):
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = None
        self.session = None
        self.stats = {
            "regioni_imported": 0,
            "comuni_imported": 0,
            "regional_rates_imported": 0,
            "communal_rates_imported": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        """Async context manager entry"""
        self.engine = create_async_engine(self.db_url, echo=False)
        async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self.session = async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.engine:
            await self.engine.dispose()

    async def import_base_regional_data(self):
        """Import base regional and municipal data"""
        logger.info("Importing base regional data...")

        try:
            # Import regions
            for region_data in DEFAULT_REGIONAL_DATA["regioni"]:
                await self._import_region(region_data)

            await self.session.commit()
            logger.info(f"Imported {len(DEFAULT_REGIONAL_DATA['regioni'])} regions")

            # Import major municipalities
            for comune_data in DEFAULT_REGIONAL_DATA["major_comuni"]:
                await self._import_comune(comune_data)

            await self.session.commit()
            logger.info(f"Imported {len(DEFAULT_REGIONAL_DATA['major_comuni'])} major comuni")

        except Exception as e:
            logger.error(f"Error importing base data: {e}")
            await self.session.rollback()
            raise

    async def _import_region(self, region_data: dict[str, Any]):
        """Import a single region"""
        try:
            # Check if region already exists
            stmt = select(Regione).where(Regione.codice_istat == region_data["codice_istat"])
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(f"Region {region_data['nome']} already exists, updating...")
                existing.nome = region_data["nome"]
                existing.capoluogo = region_data["capoluogo"]
                existing.is_autonomous = region_data["is_autonomous"]
                existing.has_special_statute = region_data["has_special_statute"]
            else:
                region = Regione(
                    id=uuid4(),
                    codice_istat=region_data["codice_istat"],
                    nome=region_data["nome"],
                    capoluogo=region_data["capoluogo"],
                    is_autonomous=region_data["is_autonomous"],
                    has_special_statute=region_data["has_special_statute"],
                )
                self.session.add(region)
                self.stats["regioni_imported"] += 1
                logger.debug(f"Added region: {region_data['nome']}")

        except Exception as e:
            logger.error(f"Error importing region {region_data.get('nome', 'unknown')}: {e}")
            self.stats["errors"] += 1

    async def _import_comune(self, comune_data: dict[str, Any]):
        """Import a single comune"""
        try:
            # Find the region
            stmt = select(Regione).where(Regione.nome == comune_data.get("regione"))
            if not comune_data.get("regione"):
                # Infer region from provincia
                provincia_to_region = {
                    "RM": "Lazio",
                    "MI": "Lombardia",
                    "NA": "Campania",
                    "TO": "Piemonte",
                    "PA": "Sicilia",
                    "FI": "Toscana",
                }
                regione_name = provincia_to_region.get(comune_data["provincia"])
                stmt = select(Regione).where(Regione.nome == regione_name)

            result = await self.session.execute(stmt)
            regione = result.scalar_one_or_none()

            if not regione:
                logger.error(f"Region not found for comune {comune_data['nome']}")
                self.stats["errors"] += 1
                return

            # Check if comune already exists
            stmt = select(Comune).where(Comune.codice_istat == comune_data["codice_istat"])
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.debug(f"Comune {comune_data['nome']} already exists, updating...")
                existing.nome = comune_data["nome"]
                existing.provincia = comune_data["provincia"]
                existing.cap_codes = comune_data["cap_codes"]
                existing.popolazione = comune_data.get("popolazione")
                existing.is_capoluogo = comune_data.get("is_capoluogo", False)
                existing.is_capoluogo_provincia = comune_data.get("is_capoluogo_provincia", False)
            else:
                comune = Comune(
                    id=uuid4(),
                    codice_istat=comune_data["codice_istat"],
                    nome=comune_data["nome"],
                    provincia=comune_data["provincia"],
                    regione_id=regione.id,
                    cap_codes=comune_data["cap_codes"],
                    popolazione=comune_data.get("popolazione"),
                    is_capoluogo=comune_data.get("is_capoluogo", False),
                    is_capoluogo_provincia=comune_data.get("is_capoluogo_provincia", False),
                )
                self.session.add(comune)
                self.stats["comuni_imported"] += 1
                logger.debug(f"Added comune: {comune_data['nome']}")

        except Exception as e:
            logger.error(f"Error importing comune {comune_data.get('nome', 'unknown')}: {e}")
            self.stats["errors"] += 1

    async def import_default_tax_rates(self):
        """Import default tax rates for major cities"""
        logger.info("Importing default tax rates...")

        try:
            # Import IMU rates
            await self._import_imu_rates()

            # Import IRAP rates
            await self._import_irap_rates()

            # Import addizionale rates
            await self._import_addizionale_rates()

            await self.session.commit()
            logger.info("Default tax rates imported successfully")

        except Exception as e:
            logger.error(f"Error importing default tax rates: {e}")
            await self.session.rollback()
            raise

    async def _import_imu_rates(self):
        """Import IMU rates for major cities"""
        for city_name, rates in DEFAULT_TAX_RATES["IMU"].items():
            try:
                # Find the comune
                stmt = select(Comune).where(Comune.nome == city_name)
                result = await self.session.execute(stmt)
                comune = result.scalar_one_or_none()

                if not comune:
                    logger.warning(f"Comune {city_name} not found for IMU rates")
                    continue

                # Check if rate already exists
                stmt = select(ComunalTaxRate).where(
                    ComunalTaxRate.comune_id == comune.id,
                    ComunalTaxRate.tax_type == "IMU",
                    ComunalTaxRate.valid_from == date(2024, 1, 1),
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    logger.debug(f"IMU rate for {city_name} already exists, updating...")
                    existing.rate = Decimal(str(rates["rate"]))
                    existing.rate_prima_casa = Decimal(str(rates.get("rate_prima_casa", 0)))
                    existing.esenzione_prima_casa = rates.get("esenzione_prima_casa", False)
                    existing.detrazioni = rates.get("detrazioni", {})
                else:
                    imu_rate = ComunalTaxRate(
                        id=uuid4(),
                        comune_id=comune.id,
                        tax_type="IMU",
                        rate=Decimal(str(rates["rate"])),
                        rate_prima_casa=Decimal(str(rates.get("rate_prima_casa", 0))),
                        esenzione_prima_casa=rates.get("esenzione_prima_casa", False),
                        valid_from=date(2024, 1, 1),
                        detrazioni=rates.get("detrazioni", {}),
                        legislative_reference="Delibere comunali 2024",
                        notes=f"Aliquota IMU {city_name} 2024",
                    )
                    self.session.add(imu_rate)
                    self.stats["communal_rates_imported"] += 1

            except Exception as e:
                logger.error(f"Error importing IMU rate for {city_name}: {e}")
                self.stats["errors"] += 1

    async def _import_irap_rates(self):
        """Import IRAP rates for regions"""
        for region_name, rates in DEFAULT_TAX_RATES["IRAP"].items():
            try:
                # Find the region
                stmt = select(Regione).where(Regione.nome == region_name)
                result = await self.session.execute(stmt)
                regione = result.scalar_one_or_none()

                if not regione:
                    logger.warning(f"Region {region_name} not found for IRAP rates")
                    continue

                # Check if rate already exists
                stmt = select(RegionalTaxRate).where(
                    RegionalTaxRate.regione_id == regione.id,
                    RegionalTaxRate.tax_type == "IRAP",
                    RegionalTaxRate.valid_from == date(2024, 1, 1),
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    logger.debug(f"IRAP rate for {region_name} already exists, updating...")
                    existing.rate_standard = Decimal(str(rates["rate_standard"]))
                    existing.rate_banks = Decimal(str(rates.get("rate_banks", 5.57)))
                    existing.rate_insurance = Decimal(str(rates.get("rate_insurance", 6.82)))
                    existing.rate_agriculture = Decimal(str(rates.get("rate_agriculture", 1.9)))
                else:
                    irap_rate = RegionalTaxRate(
                        id=uuid4(),
                        regione_id=regione.id,
                        tax_type="IRAP",
                        rate_standard=Decimal(str(rates["rate_standard"])),
                        rate_banks=Decimal(str(rates.get("rate_banks", 5.57))),
                        rate_insurance=Decimal(str(rates.get("rate_insurance", 6.82))),
                        rate_agriculture=Decimal(str(rates.get("rate_agriculture", 1.9))),
                        valid_from=date(2024, 1, 1),
                        legislative_reference="Leggi regionali 2024",
                        notes=f"Aliquote IRAP {region_name} 2024",
                    )
                    self.session.add(irap_rate)
                    self.stats["regional_rates_imported"] += 1

            except Exception as e:
                logger.error(f"Error importing IRAP rate for {region_name}: {e}")
                self.stats["errors"] += 1

    async def _import_addizionale_rates(self):
        """Import addizionale IRPEF rates"""
        # Regional addizionale
        for region_name, rate in DEFAULT_TAX_RATES["ADDIZIONALE_REGIONALE"].items():
            try:
                stmt = select(Regione).where(Regione.nome == region_name)
                result = await self.session.execute(stmt)
                regione = result.scalar_one_or_none()

                if not regione:
                    logger.warning(f"Region {region_name} not found for addizionale regionale")
                    continue

                stmt = select(RegionalTaxRate).where(
                    RegionalTaxRate.regione_id == regione.id,
                    RegionalTaxRate.tax_type == "ADDIZIONALE_IRPEF",
                    RegionalTaxRate.valid_from == date(2024, 1, 1),
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.rate_standard = Decimal(str(rate))
                else:
                    addizionale_rate = RegionalTaxRate(
                        id=uuid4(),
                        regione_id=regione.id,
                        tax_type="ADDIZIONALE_IRPEF",
                        rate_standard=Decimal(str(rate)),
                        valid_from=date(2024, 1, 1),
                        legislative_reference="Leggi regionali IRPEF 2024",
                        notes=f"Addizionale regionale IRPEF {region_name} 2024",
                    )
                    self.session.add(addizionale_rate)
                    self.stats["regional_rates_imported"] += 1

            except Exception as e:
                logger.error(f"Error importing addizionale regionale for {region_name}: {e}")
                self.stats["errors"] += 1

        # Municipal addizionale
        for city_name, rate_data in DEFAULT_TAX_RATES["ADDIZIONALE_COMUNALE"].items():
            try:
                stmt = select(Comune).where(Comune.nome == city_name)
                result = await self.session.execute(stmt)
                comune = result.scalar_one_or_none()

                if not comune:
                    logger.warning(f"Comune {city_name} not found for addizionale comunale")
                    continue

                stmt = select(ComunalTaxRate).where(
                    ComunalTaxRate.comune_id == comune.id,
                    ComunalTaxRate.tax_type == "ADDIZIONALE_COMUNALE_IRPEF",
                    ComunalTaxRate.valid_from == date(2024, 1, 1),
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                rate = rate_data["rate"] if isinstance(rate_data, dict) else rate_data
                soglie = rate_data.get("soglie", {}) if isinstance(rate_data, dict) else {}

                if existing:
                    existing.rate = Decimal(str(rate))
                    existing.soglie = soglie
                else:
                    addizionale_rate = ComunalTaxRate(
                        id=uuid4(),
                        comune_id=comune.id,
                        tax_type="ADDIZIONALE_COMUNALE_IRPEF",
                        rate=Decimal(str(rate)),
                        valid_from=date(2024, 1, 1),
                        soglie=soglie,
                        legislative_reference="Delibere comunali IRPEF 2024",
                        notes=f"Addizionale comunale IRPEF {city_name} 2024",
                    )
                    self.session.add(addizionale_rate)
                    self.stats["communal_rates_imported"] += 1

            except Exception as e:
                logger.error(f"Error importing addizionale comunale for {city_name}: {e}")
                self.stats["errors"] += 1

    async def import_from_csv(self, csv_file_path: str, import_type: str):
        """
        Import tax rates from CSV file.

        Args:
            csv_file_path: Path to CSV file
            import_type: Type of import (imu, irap, addizionale_regionale, addizionale_comunale)
        """
        logger.info(f"Importing {import_type} from CSV: {csv_file_path}")

        try:
            df = pd.read_csv(csv_file_path, encoding="utf-8")

            if import_type == "imu":
                await self._import_imu_from_csv(df)
            elif import_type == "irap":
                await self._import_irap_from_csv(df)
            elif import_type == "addizionale_regionale":
                await self._import_addizionale_regionale_from_csv(df)
            elif import_type == "addizionale_comunale":
                await self._import_addizionale_comunale_from_csv(df)
            else:
                raise ValueError(f"Unknown import type: {import_type}")

            await self.session.commit()
            logger.info(f"CSV import completed for {import_type}")

        except Exception as e:
            logger.error(f"Error importing from CSV {csv_file_path}: {e}")
            await self.session.rollback()
            raise

    async def _import_imu_from_csv(self, df: pd.DataFrame):
        """Import IMU rates from CSV DataFrame"""
        required_columns = ["codice_istat", "comune", "provincia", "aliquota_ordinaria"]

        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"CSV must contain columns: {required_columns}")

        for _, row in df.iterrows():
            try:
                # Find comune
                stmt = select(Comune).where(Comune.codice_istat == row["codice_istat"])
                result = await self.session.execute(stmt)
                comune = result.scalar_one_or_none()

                if not comune:
                    # Create comune if not exists
                    await self._create_comune_from_csv(row)
                    stmt = select(Comune).where(Comune.codice_istat == row["codice_istat"])
                    result = await self.session.execute(stmt)
                    comune = result.scalar_one_or_none()

                if not comune:
                    logger.error(f"Could not find or create comune {row['comune']}")
                    continue

                # Create or update IMU rate
                stmt = select(ComunalTaxRate).where(
                    ComunalTaxRate.comune_id == comune.id,
                    ComunalTaxRate.tax_type == "IMU",
                    ComunalTaxRate.valid_from == date(2024, 1, 1),
                )
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()

                rate_data = {
                    "rate": Decimal(str(row["aliquota_ordinaria"])),
                    "rate_prima_casa": Decimal(str(row.get("aliquota_prima_casa", 0))),
                    "esenzione_prima_casa": row.get("esenzione_prima_casa", "NO") == "SI",
                    "valid_from": date(2024, 1, 1),
                    "delibera_comunale": row.get("delibera_comunale"),
                    "notes": f"IMU {row['comune']} da CSV",
                }

                if existing:
                    for key, value in rate_data.items():
                        setattr(existing, key, value)
                else:
                    imu_rate = ComunalTaxRate(id=uuid4(), comune_id=comune.id, tax_type="IMU", **rate_data)
                    self.session.add(imu_rate)
                    self.stats["communal_rates_imported"] += 1

            except Exception as e:
                logger.error(f"Error importing IMU rate for {row.get('comune', 'unknown')}: {e}")
                self.stats["errors"] += 1

    async def _create_comune_from_csv(self, row: pd.Series):
        """Create a new comune from CSV row data"""
        try:
            # Find region by provincia
            provincia_to_region = {
                "RM": "Lazio",
                "MI": "Lombardia",
                "NA": "Campania",
                "TO": "Piemonte",
                "PA": "Sicilia",
                "FI": "Toscana",
                "BO": "Emilia-Romagna",
                "VE": "Veneto",
                "GE": "Liguria",
                "BA": "Puglia",
                "CT": "Sicilia",
                "CA": "Sardegna",
            }

            regione_name = provincia_to_region.get(row["provincia"])
            if not regione_name:
                logger.error(f"Unknown provincia: {row['provincia']}")
                return

            stmt = select(Regione).where(Regione.nome == regione_name)
            result = await self.session.execute(stmt)
            regione = result.scalar_one_or_none()

            if not regione:
                logger.error(f"Region {regione_name} not found")
                return

            # Create comune
            comune = Comune(
                id=uuid4(),
                codice_istat=row["codice_istat"],
                nome=row["comune"],
                provincia=row["provincia"],
                regione_id=regione.id,
                cap_codes=[],  # Will be populated separately
                popolazione=row.get("popolazione"),
                is_capoluogo=False,
                is_capoluogo_provincia=False,
            )

            self.session.add(comune)
            self.stats["comuni_imported"] += 1
            logger.debug(f"Created comune: {row['comune']}")

        except Exception as e:
            logger.error(f"Error creating comune from CSV: {e}")
            self.stats["errors"] += 1

    async def import_from_mef_api(self):
        """
        Import tax rates from Ministry of Economy and Finance API.

        Note: This is a placeholder for potential government API integration.
        Actual implementation would depend on available APIs.
        """
        logger.info("Importing from MEF API (placeholder)...")

        # Placeholder for actual API integration
        # This would fetch current official rates from government sources

        logger.warning("MEF API integration not yet implemented")

    async def validate_imported_data(self) -> dict[str, Any]:
        """Validate imported data for consistency and completeness"""
        logger.info("Validating imported data...")

        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "validation_passed": True,
            "issues": [],
            "statistics": {},
        }

        try:
            # Count imported records
            regioni_count = (await self.session.execute(select(Regione))).scalars().all()
            comuni_count = (await self.session.execute(select(Comune))).scalars().all()
            regional_rates_count = (await self.session.execute(select(RegionalTaxRate))).scalars().all()
            communal_rates_count = (await self.session.execute(select(ComunalTaxRate))).scalars().all()

            validation_results["statistics"] = {
                "regioni": len(regioni_count),
                "comuni": len(comuni_count),
                "regional_rates": len(regional_rates_count),
                "communal_rates": len(communal_rates_count),
            }

            # Validate required regions
            required_regions = ["Lazio", "Lombardia", "Campania", "Piemonte", "Sicilia"]
            existing_regions = [r.nome for r in regioni_count]

            for required in required_regions:
                if required not in existing_regions:
                    validation_results["issues"].append(f"Missing required region: {required}")
                    validation_results["validation_passed"] = False

            # Validate major cities have IMU rates
            major_cities = ["Roma", "Milano", "Napoli", "Torino"]
            for city in major_cities:
                city_rates = (
                    (
                        await self.session.execute(
                            select(ComunalTaxRate)
                            .join(Comune)
                            .where(Comune.nome == city, ComunalTaxRate.tax_type == "IMU")
                        )
                    )
                    .scalars()
                    .all()
                )

                if not city_rates:
                    validation_results["issues"].append(f"Missing IMU rates for {city}")
                    validation_results["validation_passed"] = False

            # Validate rate ranges
            imu_rates = (
                (await self.session.execute(select(ComunalTaxRate).where(ComunalTaxRate.tax_type == "IMU")))
                .scalars()
                .all()
            )

            for rate in imu_rates:
                if rate.rate < Decimal("0.4") or rate.rate > Decimal("1.2"):
                    validation_results["issues"].append(
                        f"IMU rate out of range for comune ID {rate.comune_id}: {rate.rate}%"
                    )

            logger.info(f"Validation completed: {len(validation_results['issues'])} issues found")

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            validation_results["validation_passed"] = False
            validation_results["issues"].append(f"Validation error: {e}")

        return validation_results

    def print_import_summary(self):
        """Print import statistics summary"""
        print("\n" + "=" * 50)
        print("REGIONAL TAX IMPORT SUMMARY")
        print("=" * 50)
        print(f"Regioni imported:        {self.stats['regioni_imported']}")
        print(f"Comuni imported:         {self.stats['comuni_imported']}")
        print(f"Regional rates imported: {self.stats['regional_rates_imported']}")
        print(f"Communal rates imported: {self.stats['communal_rates_imported']}")
        print(f"Errors encountered:      {self.stats['errors']}")
        print("=" * 50)


async def main():
    """Main import function"""
    print("Starting Regional Tax Rate Import...")

    async with RegionalTaxImporter() as importer:
        try:
            # Import base data
            await importer.import_base_regional_data()

            # Import default tax rates
            await importer.import_default_tax_rates()

            # Validate imported data
            validation = await importer.validate_imported_data()

            # Print summary
            importer.print_import_summary()

            # Print validation results
            print(f"\nValidation Status: {'PASSED' if validation['validation_passed'] else 'FAILED'}")
            if validation["issues"]:
                print("Issues found:")
                for issue in validation["issues"]:
                    print(f"  - {issue}")

            print("\nDatabase contains:")
            for key, value in validation["statistics"].items():
                print(f"  - {key}: {value}")

        except Exception as e:
            logger.error(f"Import failed: {e}")
            print(f"\nIMPORT FAILED: {e}")
            return 1

    print("\nImport completed successfully!")
    return 0


if __name__ == "__main__":
    import sys

    # Handle command line arguments
    if len(sys.argv) > 1:
        action = sys.argv[1]

        if action == "csv" and len(sys.argv) > 3:
            csv_file = sys.argv[2]
            import_type = sys.argv[3]

            async def import_csv():
                async with RegionalTaxImporter() as importer:
                    await importer.import_from_csv(csv_file, import_type)
                    importer.print_import_summary()

            asyncio.run(import_csv())

        elif action == "validate":

            async def validate_only():
                async with RegionalTaxImporter() as importer:
                    validation = await importer.validate_imported_data()
                    print(json.dumps(validation, indent=2))

            asyncio.run(validate_only())

        else:
            print("Usage:")
            print("  python import_regional_rates.py              # Full import")
            print("  python import_regional_rates.py csv <file> <type>  # Import from CSV")
            print("  python import_regional_rates.py validate     # Validate only")
            sys.exit(1)
    else:
        # Run full import
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
