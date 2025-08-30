"""
Italian Location Service for Geographic Data Management.

This service handles Italian geographic data including CAP to comune mapping,
provincia to region relationships, and location validation.
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal

from app.services.cache import CacheService
from app.core.logging import logger


# Custom Exceptions

class InvalidCAP(Exception):
    """Raised when CAP format is invalid"""
    pass


class LocationAmbiguous(Exception):
    """Raised when location lookup returns multiple matches"""
    pass


class ItalianLocationService:
    """
    Service for handling Italian geographic data and mappings.
    
    Provides CAP to city mapping, provincia to region relationships,
    and validation of Italian postal codes and geographic identifiers.
    """
    
    def __init__(self, db=None, cache_service: Optional[CacheService] = None):
        self.db = db
        self.cache = cache_service
        
        # Static mappings for fast lookups and fallbacks
        self.init_static_mappings()
    
    def init_static_mappings(self):
        """Initialize static geographic mappings"""
        
        # CAP to major city mapping (partial list for fallback)
        self.CAP_TO_CITY = {
            # Roma
            "00100": "Roma", "00118": "Roma", "00119": "Roma", "00120": "Roma",
            "00121": "Roma", "00122": "Roma", "00123": "Roma", "00124": "Roma",
            "00125": "Roma", "00126": "Roma", "00127": "Roma", "00128": "Roma",
            "00129": "Roma", "00131": "Roma", "00132": "Roma", "00133": "Roma",
            "00134": "Roma", "00135": "Roma", "00136": "Roma", "00137": "Roma",
            "00138": "Roma", "00139": "Roma", "00141": "Roma", "00142": "Roma",
            "00143": "Roma", "00144": "Roma", "00145": "Roma", "00146": "Roma",
            "00147": "Roma", "00148": "Roma", "00149": "Roma", "00151": "Roma",
            "00152": "Roma", "00153": "Roma", "00154": "Roma", "00155": "Roma",
            "00156": "Roma", "00157": "Roma", "00158": "Roma", "00159": "Roma",
            "00161": "Roma", "00162": "Roma", "00163": "Roma", "00164": "Roma",
            "00165": "Roma", "00166": "Roma", "00167": "Roma", "00168": "Roma",
            "00169": "Roma", "00171": "Roma", "00172": "Roma", "00173": "Roma",
            "00174": "Roma", "00175": "Roma", "00176": "Roma", "00177": "Roma",
            "00178": "Roma", "00179": "Roma", "00181": "Roma", "00182": "Roma",
            "00183": "Roma", "00184": "Roma", "00185": "Roma", "00186": "Roma",
            "00187": "Roma", "00188": "Roma", "00189": "Roma", "00191": "Roma",
            "00192": "Roma", "00193": "Roma", "00194": "Roma", "00195": "Roma",
            "00196": "Roma", "00197": "Roma", "00198": "Roma", "00199": "Roma",
            
            # Milano
            "20100": "Milano", "20121": "Milano", "20122": "Milano", "20123": "Milano",
            "20124": "Milano", "20125": "Milano", "20126": "Milano", "20127": "Milano",
            "20128": "Milano", "20129": "Milano", "20131": "Milano", "20132": "Milano",
            "20133": "Milano", "20134": "Milano", "20135": "Milano", "20136": "Milano",
            "20137": "Milano", "20138": "Milano", "20139": "Milano", "20141": "Milano",
            "20142": "Milano", "20143": "Milano", "20144": "Milano", "20145": "Milano",
            "20146": "Milano", "20147": "Milano", "20148": "Milano", "20149": "Milano",
            "20151": "Milano", "20152": "Milano", "20153": "Milano", "20154": "Milano",
            "20155": "Milano", "20156": "Milano", "20157": "Milano", "20158": "Milano",
            "20159": "Milano", "20161": "Milano", "20162": "Milano",
            
            # Napoli
            "80100": "Napoli", "80121": "Napoli", "80122": "Napoli", "80123": "Napoli",
            "80124": "Napoli", "80125": "Napoli", "80126": "Napoli", "80127": "Napoli",
            "80128": "Napoli", "80129": "Napoli", "80131": "Napoli", "80132": "Napoli",
            "80133": "Napoli", "80134": "Napoli", "80135": "Napoli", "80136": "Napoli",
            "80137": "Napoli", "80138": "Napoli", "80139": "Napoli", "80141": "Napoli",
            "80142": "Napoli", "80143": "Napoli", "80144": "Napoli", "80145": "Napoli",
            "80146": "Napoli", "80147": "Napoli",
            
            # Torino
            "10100": "Torino", "10121": "Torino", "10122": "Torino", "10123": "Torino",
            "10124": "Torino", "10125": "Torino", "10126": "Torino", "10127": "Torino",
            "10128": "Torino", "10129": "Torino", "10131": "Torino", "10132": "Torino",
            "10133": "Torino", "10134": "Torino", "10135": "Torino", "10136": "Torino",
            "10137": "Torino", "10138": "Torino", "10139": "Torino", "10141": "Torino",
            "10142": "Torino", "10143": "Torino", "10144": "Torino", "10145": "Torino",
            "10146": "Torino", "10147": "Torino", "10148": "Torino", "10149": "Torino",
            "10151": "Torino", "10152": "Torino", "10153": "Torino", "10154": "Torino",
            "10155": "Torino", "10156": "Torino",
            
            # Palermo
            "90100": "Palermo", "90121": "Palermo", "90122": "Palermo", "90123": "Palermo",
            "90124": "Palermo", "90125": "Palermo", "90126": "Palermo", "90127": "Palermo",
            "90128": "Palermo", "90129": "Palermo", "90131": "Palermo", "90133": "Palermo",
            "90134": "Palermo", "90135": "Palermo", "90136": "Palermo", "90137": "Palermo",
            "90138": "Palermo", "90139": "Palermo", "90141": "Palermo", "90142": "Palermo",
            "90143": "Palermo", "90144": "Palermo", "90145": "Palermo", "90146": "Palermo",
            
            # Firenze
            "50100": "Firenze", "50121": "Firenze", "50122": "Firenze", "50123": "Firenze",
            "50124": "Firenze", "50125": "Firenze", "50126": "Firenze", "50127": "Firenze",
            "50128": "Firenze", "50129": "Firenze", "50131": "Firenze", "50132": "Firenze",
            "50133": "Firenze", "50134": "Firenze", "50135": "Firenze", "50136": "Firenze",
            "50137": "Firenze", "50138": "Firenze", "50139": "Firenze", "50141": "Firenze",
            "50142": "Firenze", "50143": "Firenze", "50144": "Firenze", "50145": "Firenze",
            
            # Bologna
            "40100": "Bologna", "40121": "Bologna", "40122": "Bologna", "40123": "Bologna",
            "40124": "Bologna", "40125": "Bologna", "40126": "Bologna", "40127": "Bologna",
            "40128": "Bologna", "40129": "Bologna", "40131": "Bologna", "40132": "Bologna",
            "40133": "Bologna", "40134": "Bologna", "40135": "Bologna", "40136": "Bologna",
            "40137": "Bologna", "40138": "Bologna", "40139": "Bologna", "40141": "Bologna",
            "40142": "Bologna", "40143": "Bologna", "40144": "Bologna", "40145": "Bologna"
        }
        
        # Provincia to Region mapping
        self.PROVINCIA_TO_REGIONE = {
            # Abruzzo
            "AQ": "Abruzzo", "CH": "Abruzzo", "PE": "Abruzzo", "TE": "Abruzzo",
            
            # Basilicata
            "MT": "Basilicata", "PZ": "Basilicata",
            
            # Calabria
            "CS": "Calabria", "CZ": "Calabria", "KR": "Calabria", "RC": "Calabria", "VV": "Calabria",
            
            # Campania
            "AV": "Campania", "BN": "Campania", "CE": "Campania", "NA": "Campania", "SA": "Campania",
            
            # Emilia-Romagna
            "BO": "Emilia-Romagna", "FC": "Emilia-Romagna", "FE": "Emilia-Romagna",
            "MO": "Emilia-Romagna", "PC": "Emilia-Romagna", "PR": "Emilia-Romagna",
            "RA": "Emilia-Romagna", "RE": "Emilia-Romagna", "RN": "Emilia-Romagna",
            
            # Friuli-Venezia Giulia
            "GO": "Friuli-Venezia Giulia", "PN": "Friuli-Venezia Giulia",
            "TS": "Friuli-Venezia Giulia", "UD": "Friuli-Venezia Giulia",
            
            # Lazio
            "FR": "Lazio", "LT": "Lazio", "RI": "Lazio", "RM": "Lazio", "VT": "Lazio",
            
            # Liguria
            "GE": "Liguria", "IM": "Liguria", "SP": "Liguria", "SV": "Liguria",
            
            # Lombardia
            "BG": "Lombardia", "BS": "Lombardia", "CO": "Lombardia", "CR": "Lombardia",
            "LC": "Lombardia", "LO": "Lombardia", "MN": "Lombardia", "MI": "Lombardia",
            "PV": "Lombardia", "SO": "Lombardia", "VA": "Lombardia", "MB": "Lombardia",
            
            # Marche
            "AN": "Marche", "AP": "Marche", "FM": "Marche", "MC": "Marche", "PU": "Marche",
            
            # Molise
            "CB": "Molise", "IS": "Molise",
            
            # Piemonte
            "AL": "Piemonte", "AT": "Piemonte", "BI": "Piemonte", "CN": "Piemonte",
            "NO": "Piemonte", "TO": "Piemonte", "VB": "Piemonte", "VC": "Piemonte",
            
            # Puglia
            "BA": "Puglia", "BT": "Puglia", "BR": "Puglia", "FG": "Puglia", "LE": "Puglia", "TA": "Puglia",
            
            # Sardegna
            "CA": "Sardegna", "CI": "Sardegna", "NU": "Sardegna", "OG": "Sardegna", 
            "OR": "Sardegna", "SS": "Sardegna", "SU": "Sardegna", "VS": "Sardegna",
            
            # Sicilia
            "AG": "Sicilia", "CL": "Sicilia", "CT": "Sicilia", "EN": "Sicilia",
            "ME": "Sicilia", "PA": "Sicilia", "RG": "Sicilia", "SR": "Sicilia", "TP": "Sicilia",
            
            # Toscana
            "AR": "Toscana", "FI": "Toscana", "GR": "Toscana", "LI": "Toscana",
            "LU": "Toscana", "MS": "Toscana", "PI": "Toscana", "PO": "Toscana",
            "PT": "Toscana", "SI": "Toscana",
            
            # Trentino-Alto Adige
            "BZ": "Trentino-Alto Adige", "TN": "Trentino-Alto Adige",
            
            # Umbria
            "PG": "Umbria", "TR": "Umbria",
            
            # Valle d'Aosta
            "AO": "Valle d'Aosta",
            
            # Veneto
            "BL": "Veneto", "PD": "Veneto", "RO": "Veneto", "TV": "Veneto",
            "VE": "Veneto", "VI": "Veneto", "VR": "Veneto"
        }
        
        # Major city populations (for validation and sorting)
        self.CITY_POPULATIONS = {
            "Roma": 2872800,
            "Milano": 1396059,
            "Napoli": 967069,
            "Torino": 870952,
            "Palermo": 676118,
            "Genova": 583601,
            "Bologna": 394843,
            "Firenze": 382258,
            "Bari": 325052,
            "Catania": 315601,
            "Venezia": 261905,
            "Verona": 259610,
            "Messina": 238439,
            "Padova": 214125,
            "Trieste": 204338,
            "Brescia": 196745,
            "Taranto": 194021,
            "Prato": 195213,
            "Parma": 198292,
            "Reggio Calabria": 182551
        }
        
        # Region population and area data
        self.REGION_DATA = {
            "Lombardia": {"popolazione": 10103969, "area_kmq": 23844, "capoluogo": "Milano"},
            "Lazio": {"popolazione": 5879082, "area_kmq": 17232, "capoluogo": "Roma"},
            "Campania": {"popolazione": 5801692, "area_kmq": 13671, "capoluogo": "Napoli"},
            "Sicilia": {"popolazione": 4999891, "area_kmq": 25832, "capoluogo": "Palermo"},
            "Veneto": {"popolazione": 4905854, "area_kmq": 18345, "capoluogo": "Venezia"},
            "Emilia-Romagna": {"popolazione": 4459477, "area_kmq": 22452, "capoluogo": "Bologna"},
            "Piemonte": {"popolazione": 4356406, "area_kmq": 25387, "capoluogo": "Torino"},
            "Puglia": {"popolazione": 4029053, "area_kmq": 19540, "capoluogo": "Bari"},
            "Toscana": {"popolazione": 3729641, "area_kmq": 22987, "capoluogo": "Firenze"},
            "Calabria": {"popolazione": 1947131, "area_kmq": 15222, "capoluogo": "Catanzaro"},
            "Sardegna": {"popolazione": 1648176, "area_kmq": 24100, "capoluogo": "Cagliari"},
            "Liguria": {"popolazione": 1550640, "area_kmq": 5416, "capoluogo": "Genova"},
            "Marche": {"popolazione": 1525271, "area_kmq": 9366, "capoluogo": "Ancona"},
            "Abruzzo": {"popolazione": 1311580, "area_kmq": 10832, "capoluogo": "L'Aquila"},
            "Friuli-Venezia Giulia": {"popolazione": 1215220, "area_kmq": 7862, "capoluogo": "Trieste"},
            "Trentino-Alto Adige": {"popolazione": 1074819, "area_kmq": 13605, "capoluogo": "Trento"},
            "Umbria": {"popolazione": 882015, "area_kmq": 8456, "capoluogo": "Perugia"},
            "Basilicata": {"popolazione": 562869, "area_kmq": 10073, "capoluogo": "Potenza"},
            "Molise": {"popolazione": 305617, "area_kmq": 4461, "capoluogo": "Campobasso"},
            "Valle d'Aosta": {"popolazione": 125666, "area_kmq": 3260, "capoluogo": "Aosta"}
        }
    
    async def validate_cap(self, cap: str) -> bool:
        """
        Validate Italian postal code format.
        
        Args:
            cap: Italian postal code
            
        Returns:
            True if valid, False otherwise
        """
        if not cap:
            return False
        
        # Remove spaces and convert to string
        cap = str(cap).replace(" ", "")
        
        # Must be exactly 5 digits
        if len(cap) != 5:
            return False
        
        # Must be all numeric
        if not cap.isdigit():
            return False
        
        # First digit cannot be 0 (except for some special cases like Vatican 00120)
        # Actually, Italian CAPs can start with 0 (Roma area)
        return True
    
    async def get_location_from_cap(self, cap: str) -> Dict[str, Any]:
        """
        Get complete location information from CAP.
        
        Args:
            cap: Italian postal code
            
        Returns:
            Dictionary with location information
            
        Raises:
            InvalidCAP: If CAP format is invalid
            LocationNotFound: If location cannot be determined
        """
        if not await self.validate_cap(cap):
            raise InvalidCAP(f"CAP non valido: {cap}")
        
        cap = cap.strip()
        
        # Try cache first
        if self.cache:
            cache_key = f"location:cap:{cap}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        location = None
        
        # Try database lookup first if available
        if self.db:
            try:
                result = await self.db.execute("""
                    SELECT 
                        c.nome as comune,
                        c.provincia,
                        r.nome as regione,
                        c.popolazione,
                        c.is_capoluogo,
                        c.is_capoluogo_provincia,
                        c.area_kmq,
                        c.latitudine,
                        c.longitudine
                    FROM comuni c
                    JOIN regioni r ON c.regione_id = r.id
                    WHERE $1 = ANY(c.cap_codes)
                    LIMIT 1
                """, cap)
                
                if result:
                    location = {
                        "cap": cap,
                        "comune": result.comune,
                        "provincia": result.provincia,
                        "regione": result.regione,
                        "popolazione": result.popolazione,
                        "is_capoluogo": result.is_capoluogo,
                        "is_capoluogo_provincia": result.is_capoluogo_provincia,
                        "area_kmq": float(result.area_kmq) if result.area_kmq else None,
                        "coordinates": {
                            "lat": float(result.latitudine) if result.latitudine else None,
                            "lng": float(result.longitudine) if result.longitudine else None
                        }
                    }
            except Exception as e:
                logger.warning(f"Database lookup failed for CAP {cap}: {e}")
        
        # Fallback to static mapping if database lookup failed
        if not location:
            comune = self.CAP_TO_CITY.get(cap)
            if comune:
                provincia = self._get_provincia_from_comune(comune)
                regione = self.PROVINCIA_TO_REGIONE.get(provincia, "Unknown")
                popolazione = self.CITY_POPULATIONS.get(comune, 0)
                
                location = {
                    "cap": cap,
                    "comune": comune,
                    "provincia": provincia,
                    "regione": regione,
                    "popolazione": popolazione,
                    "is_capoluogo": comune in ["Roma", "Milano", "Napoli", "Torino", "Palermo"],
                    "is_capoluogo_provincia": True,  # Major cities are typically provincial capitals
                    "area_kmq": None,
                    "coordinates": {"lat": None, "lng": None},
                    "source": "static_mapping"
                }
        
        if not location:
            # Try to infer from CAP prefix
            location = self._infer_location_from_cap_prefix(cap)
        
        if not location:
            raise LocationNotFound(f"Località non trovata per CAP {cap}")
        
        # Cache the result
        if self.cache and location:
            await self.cache.set(f"location:cap:{cap}", location, ttl=86400)  # 24 hours
        
        return location
    
    def _get_provincia_from_comune(self, comune: str) -> str:
        """Get provincia abbreviation from comune name"""
        provincia_mappings = {
            "Roma": "RM", "Milano": "MI", "Napoli": "NA", "Torino": "TO",
            "Palermo": "PA", "Genova": "GE", "Bologna": "BO", "Firenze": "FI",
            "Bari": "BA", "Catania": "CT", "Venezia": "VE", "Verona": "VR",
            "Messina": "ME", "Padova": "PD", "Trieste": "TS", "Brescia": "BS",
            "Taranto": "TA", "Prato": "PO", "Parma": "PR", "Reggio Calabria": "RC"
        }
        return provincia_mappings.get(comune, "XX")
    
    def _infer_location_from_cap_prefix(self, cap: str) -> Optional[Dict[str, Any]]:
        """Infer location from CAP prefix when exact match not found"""
        prefix = cap[:2]
        
        # Major regional prefixes
        prefix_regions = {
            "00": {"regione": "Lazio", "provincia_likely": "RM"},
            "20": {"regione": "Lombardia", "provincia_likely": "MI"},
            "80": {"regione": "Campania", "provincia_likely": "NA"},
            "10": {"regione": "Piemonte", "provincia_likely": "TO"},
            "90": {"regione": "Sicilia", "provincia_likely": "PA"},
            "50": {"regione": "Toscana", "provincia_likely": "FI"},
            "40": {"regione": "Emilia-Romagna", "provincia_likely": "BO"},
            "16": {"regione": "Liguria", "provincia_likely": "GE"},
            "30": {"regione": "Veneto", "provincia_likely": "VE"},
            "70": {"regione": "Puglia", "provincia_likely": "BA"},
            "60": {"regione": "Marche", "provincia_likely": "AN"},
            "95": {"regione": "Sicilia", "provincia_likely": "CT"}
        }
        
        region_info = prefix_regions.get(prefix)
        if region_info:
            return {
                "cap": cap,
                "comune": "Unknown",
                "provincia": region_info["provincia_likely"],
                "regione": region_info["regione"],
                "popolazione": None,
                "is_capoluogo": False,
                "is_capoluogo_provincia": False,
                "area_kmq": None,
                "coordinates": {"lat": None, "lng": None},
                "source": "prefix_inference",
                "note": f"Località inferita dal prefisso CAP {prefix}"
            }
        
        return None
    
    async def search_locations(
        self,
        query: str,
        limit: int = 10,
        region_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for locations by name with optional region filtering.
        
        Args:
            query: Search query (comune or provincia name)
            limit: Maximum number of results
            region_filter: Optional region name to filter results
            
        Returns:
            List of matching locations
        """
        results = []
        
        # Search in static mappings first
        query_lower = query.lower()
        
        # Search comuni
        for cap, comune in self.CAP_TO_CITY.items():
            if query_lower in comune.lower():
                try:
                    location = await self.get_location_from_cap(cap)
                    if region_filter and location["regione"].lower() != region_filter.lower():
                        continue
                    results.append(location)
                    if len(results) >= limit:
                        break
                except Exception:
                    continue
        
        # Search province abbreviations
        for prov, regione in self.PROVINCIA_TO_REGIONE.items():
            if query_lower in prov.lower() or query_lower in regione.lower():
                if region_filter and regione.lower() != region_filter.lower():
                    continue
                
                # Find a CAP for this provincia
                sample_cap = self._get_sample_cap_for_provincia(prov)
                if sample_cap:
                    try:
                        location = await self.get_location_from_cap(sample_cap)
                        results.append(location)
                        if len(results) >= limit:
                            break
                    except Exception:
                        continue
        
        # Remove duplicates and sort by population
        unique_results = []
        seen_locations = set()
        
        for result in results:
            location_key = f"{result['comune']}-{result['provincia']}"
            if location_key not in seen_locations:
                seen_locations.add(location_key)
                unique_results.append(result)
        
        # Sort by population (highest first)
        unique_results.sort(key=lambda x: x.get('popolazione', 0), reverse=True)
        
        return unique_results[:limit]
    
    def _get_sample_cap_for_provincia(self, provincia: str) -> Optional[str]:
        """Get a sample CAP for a given provincia"""
        for cap, comune in self.CAP_TO_CITY.items():
            expected_prov = self._get_provincia_from_comune(comune)
            if expected_prov == provincia:
                return cap
        return None
    
    async def get_distance_between_caps(self, cap1: str, cap2: str) -> Optional[float]:
        """
        Calculate approximate distance between two CAPs.
        
        Args:
            cap1: First postal code
            cap2: Second postal code
            
        Returns:
            Distance in kilometers, or None if coordinates unavailable
        """
        try:
            loc1 = await self.get_location_from_cap(cap1)
            loc2 = await self.get_location_from_cap(cap2)
            
            coord1 = loc1.get("coordinates", {})
            coord2 = loc2.get("coordinates", {})
            
            if (coord1.get("lat") and coord1.get("lng") and 
                coord2.get("lat") and coord2.get("lng")):
                
                return self._haversine_distance(
                    coord1["lat"], coord1["lng"],
                    coord2["lat"], coord2["lng"]
                )
        except Exception as e:
            logger.warning(f"Could not calculate distance between {cap1} and {cap2}: {e}")
        
        return None
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    async def validate_italian_address(self, address_components: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate Italian address components.
        
        Args:
            address_components: Dictionary with address parts
                - cap: postal code
                - comune: municipality name
                - provincia: province abbreviation
                - regione: region name (optional)
                
        Returns:
            Validation result with corrections and suggestions
        """
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "corrections": {},
            "confidence": 1.0
        }
        
        cap = address_components.get("cap", "").strip()
        comune = address_components.get("comune", "").strip()
        provincia = address_components.get("provincia", "").strip().upper()
        regione = address_components.get("regione", "").strip()
        
        # Validate CAP
        if cap:
            if not await self.validate_cap(cap):
                result["errors"].append(f"CAP non valido: {cap}")
                result["is_valid"] = False
            else:
                try:
                    cap_location = await self.get_location_from_cap(cap)
                    
                    # Check consistency with provided comune
                    if comune and comune.lower() != cap_location["comune"].lower():
                        result["warnings"].append(
                            f"Il comune '{comune}' non corrisponde al CAP {cap} "
                            f"(previsto: {cap_location['comune']})"
                        )
                        result["corrections"]["comune"] = cap_location["comune"]
                        result["confidence"] *= 0.8
                    
                    # Check consistency with provided provincia
                    if provincia and provincia != cap_location["provincia"]:
                        result["warnings"].append(
                            f"La provincia '{provincia}' non corrisponde al CAP {cap} "
                            f"(prevista: {cap_location['provincia']})"
                        )
                        result["corrections"]["provincia"] = cap_location["provincia"]
                        result["confidence"] *= 0.8
                    
                    # Check consistency with provided regione
                    if regione and regione.lower() != cap_location["regione"].lower():
                        result["warnings"].append(
                            f"La regione '{regione}' non corrisponde al CAP {cap} "
                            f"(prevista: {cap_location['regione']})"
                        )
                        result["corrections"]["regione"] = cap_location["regione"]
                        result["confidence"] *= 0.8
                    
                except Exception as e:
                    result["errors"].append(f"Impossibile verificare il CAP {cap}: {e}")
                    result["is_valid"] = False
        
        # Validate provincia
        if provincia and provincia not in self.PROVINCIA_TO_REGIONE:
            result["errors"].append(f"Codice provincia non valido: {provincia}")
            result["is_valid"] = False
            
            # Suggest similar province codes
            similar = [p for p in self.PROVINCIA_TO_REGIONE.keys() 
                      if abs(len(p) - len(provincia)) <= 1]
            if similar:
                result["corrections"]["provincia_suggestions"] = similar[:3]
        
        # Validate regione
        if regione:
            found_regione = False
            for reg_name in self.REGION_DATA.keys():
                if regione.lower() == reg_name.lower():
                    found_regione = True
                    break
            
            if not found_regione:
                result["warnings"].append(f"Nome regione non riconosciuto: {regione}")
                result["confidence"] *= 0.9
                
                # Suggest similar region names
                similar_regions = [r for r in self.REGION_DATA.keys() 
                                 if regione.lower() in r.lower() or r.lower() in regione.lower()]
                if similar_regions:
                    result["corrections"]["regione_suggestions"] = similar_regions[:3]
        
        return result
    
    async def get_nearby_locations(
        self,
        cap: str,
        radius_km: float = 50,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get nearby locations within specified radius.
        
        Args:
            cap: Central postal code
            radius_km: Search radius in kilometers
            limit: Maximum number of results
            
        Returns:
            List of nearby locations with distances
        """
        try:
            center_location = await self.get_location_from_cap(cap)
            center_coords = center_location.get("coordinates", {})
            
            if not (center_coords.get("lat") and center_coords.get("lng")):
                # If no coordinates available, return locations in same region
                return await self._get_locations_same_region(center_location["regione"], limit)
            
            nearby = []
            
            # Search through major cities
            for sample_cap, comune in list(self.CAP_TO_CITY.items())[:100]:  # Limit search
                if sample_cap == cap:
                    continue
                
                try:
                    location = await self.get_location_from_cap(sample_cap)
                    coords = location.get("coordinates", {})
                    
                    if coords.get("lat") and coords.get("lng"):
                        distance = self._haversine_distance(
                            center_coords["lat"], center_coords["lng"],
                            coords["lat"], coords["lng"]
                        )
                        
                        if distance <= radius_km:
                            location["distance_km"] = round(distance, 1)
                            nearby.append(location)
                
                except Exception:
                    continue
            
            # Sort by distance and limit results
            nearby.sort(key=lambda x: x.get("distance_km", float('inf')))
            return nearby[:limit]
            
        except Exception as e:
            logger.warning(f"Could not find nearby locations for {cap}: {e}")
            return []
    
    async def _get_locations_same_region(self, regione: str, limit: int) -> List[Dict[str, Any]]:
        """Get locations in the same region as fallback"""
        locations = []
        
        for cap, comune in self.CAP_TO_CITY.items():
            try:
                location = await self.get_location_from_cap(cap)
                if location["regione"] == regione:
                    locations.append(location)
                    if len(locations) >= limit:
                        break
            except Exception:
                continue
        
        return locations
    
    async def get_region_statistics(self, regione_name: str) -> Dict[str, Any]:
        """Get statistical information about a region"""
        region_data = self.REGION_DATA.get(regione_name)
        if not region_data:
            return {"error": f"Regione {regione_name} non trovata"}
        
        # Count province in this region
        province_count = sum(1 for r in self.PROVINCIA_TO_REGIONE.values() if r == regione_name)
        
        # Get major cities in this region
        major_cities = []
        for cap, comune in self.CAP_TO_CITY.items():
            try:
                location = await self.get_location_from_cap(cap)
                if location["regione"] == regione_name and location.get("popolazione", 0) > 100000:
                    major_cities.append({
                        "nome": comune,
                        "popolazione": location.get("popolazione", 0),
                        "is_capoluogo": location.get("is_capoluogo", False)
                    })
            except Exception:
                continue
        
        major_cities.sort(key=lambda x: x["popolazione"], reverse=True)
        
        return {
            "nome": regione_name,
            "popolazione": region_data["popolazione"],
            "area_kmq": region_data["area_kmq"],
            "capoluogo": region_data["capoluogo"],
            "densita_abitativa": round(region_data["popolazione"] / region_data["area_kmq"], 1),
            "numero_province": province_count,
            "citta_principali": major_cities[:10],
            "is_autonomous": regione_name in ["Sicilia", "Sardegna", "Trentino-Alto Adige", "Valle d'Aosta", "Friuli-Venezia Giulia"]
        }