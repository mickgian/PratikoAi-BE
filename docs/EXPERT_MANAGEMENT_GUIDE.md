# Expert Management Guide - Manual Expert Creation

## Overview

This guide provides step-by-step instructions for manually creating and managing expert profiles in PratikoAI's expert feedback system. Since there's no automated expert registration API, all expert profiles must be created manually through database operations.

## Prerequisites

- Database access to PratikoAI's PostgreSQL instance
- Understanding of Italian tax professional credentials
- Access to verify professional registration numbers

## Expert Profile Structure

Each expert requires the following information:

### Required Fields
```python
user_id: UUID                    # Link to existing user account
credentials: List[str]           # Professional credentials (see below)
experience_years: int           # Years of professional experience
is_verified: bool              # Manual verification status
is_active: bool                # Enable/disable expert feedback collection
```

### Optional Fields
```python
credential_types: List[ExpertCredentialType]  # Enum versions of credentials
specializations: List[str]                   # Areas of expertise
professional_registration_number: str        # Official registration number
organization: str                           # Professional organization/firm
location_city: str                          # City/region of practice
trust_score: float                          # Defaults to 0.5, system will optimize
```

## Italian Professional Credentials

### Credential Types and Trust Score Weights

| Credential | Italian Name | Trust Weight | Requirements |
|------------|-------------|--------------|--------------|
| `dottore_commercialista` | Dottore Commercialista | 0.30 (30%) | Registered with CNDCEC |
| `revisore_legale` | Revisore Legale | 0.25 (25%) | Registered with MEF |
| `consulente_fiscale` | Consulente Fiscale | 0.20 (20%) | Specialized tax advisor |
| `consulente_lavoro` | Consulente del Lavoro | 0.15 (15%) | Labor law specialist |
| `caf_operator` | Operatore CAF | 0.10 (10%) | CAF center operator |

### Credential Verification Checklist

Before creating an expert profile, verify:
- [ ] **Professional Registration**: Check with relevant Italian authority
- [ ] **Active Status**: Ensure registration is current and active
- [ ] **Specializations**: Confirm areas of tax expertise
- [ ] **Experience**: Validate years of professional practice
- [ ] **Good Standing**: No disciplinary actions or suspensions

## Step-by-Step Expert Creation Process

### Step 1: Verify User Account Exists

```sql
-- Check if user account exists
SELECT id, email FROM users WHERE email = 'expert@example.com';
```

If no user exists, create one first through the regular registration process.

### Step 2: Create Expert Profile

```sql
-- Insert expert profile
INSERT INTO expert_profiles (
    id,
    user_id,
    credentials,
    credential_types,
    experience_years,
    specializations,
    professional_registration_number,
    organization,
    location_city,
    trust_score,
    is_verified,
    is_active,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),                                    -- Auto-generate UUID
    '12345678-1234-1234-1234-123456789012',              -- user_id from Step 1
    ARRAY['dottore_commercialista'],                      -- credentials array
    ARRAY['dottore_commercialista'::expertcredentialtype], -- credential_types enum
    15,                                                   -- experience_years
    ARRAY['fiscale', 'iva', 'societario'],               -- specializations
    'DC-12345',                                           -- registration number
    'Studio Commercialista Rossi',                       -- organization
    'Milano',                                             -- location_city
    0.5,                                                  -- trust_score (default)
    true,                                                 -- is_verified
    true,                                                 -- is_active
    NOW(),                                                -- created_at
    NOW()                                                 -- updated_at
);
```

### Step 3: Verify Creation

```sql
-- Verify expert was created successfully
SELECT 
    id,
    user_id,
    credentials,
    experience_years,
    trust_score,
    is_verified,
    is_active
FROM expert_profiles 
WHERE user_id = '12345678-1234-1234-1234-123456789012';
```

## Python Script for Expert Creation

For easier expert management, here's a Python script:

```python
#!/usr/bin/env python3
"""
Expert Profile Creation Script for PratikoAI

Usage: python create_expert.py --email expert@email.com --credentials dottore_commercialista --years 15
"""

import asyncio
import sys
import uuid
from typing import List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.quality_analysis import ExpertProfile, ExpertCredentialType

class ExpertCreator:
    """Helper class for creating expert profiles manually."""
    
    def __init__(self):
        self.engine = create_engine(settings.POSTGRES_URL)
    
    async def create_expert_profile(
        self,
        email: str,
        credentials: List[str],
        experience_years: int,
        specializations: Optional[List[str]] = None,
        organization: Optional[str] = None,
        location_city: Optional[str] = None,
        registration_number: Optional[str] = None
    ) -> str:
        """
        Create expert profile for given email.
        
        Args:
            email: Expert's email address (must have existing user account)
            credentials: List of professional credentials
            experience_years: Years of professional experience
            specializations: Areas of expertise (optional)
            organization: Professional organization/firm (optional)
            location_city: City/region of practice (optional)
            registration_number: Official registration number (optional)
            
        Returns:
            Expert profile ID
        """
        
        with Session(self.engine) as session:
            try:
                # 1. Find user ID by email
                user_query = text("SELECT id FROM users WHERE email = :email")
                user_result = session.execute(user_query, {"email": email}).fetchone()
                
                if not user_result:
                    raise ValueError(f"User with email {email} not found. Create user account first.")
                
                user_id = user_result.id
                
                # 2. Validate credentials
                valid_credentials = [
                    "dottore_commercialista",
                    "revisore_legale", 
                    "consulente_fiscale",
                    "consulente_lavoro",
                    "caf_operator"
                ]
                
                for cred in credentials:
                    if cred not in valid_credentials:
                        raise ValueError(f"Invalid credential: {cred}. Valid options: {valid_credentials}")
                
                # 3. Generate expert profile ID
                expert_id = str(uuid.uuid4())
                
                # 4. Create expert profile
                expert_data = {
                    "id": expert_id,
                    "user_id": str(user_id),
                    "credentials": credentials,
                    "credential_types": credentials,  # Same values for enum
                    "experience_years": experience_years,
                    "specializations": specializations or [],
                    "professional_registration_number": registration_number,
                    "organization": organization,
                    "location_city": location_city,
                    "trust_score": 0.5,  # Default starting score
                    "feedback_count": 0,
                    "feedback_accuracy_rate": 0.0,
                    "average_response_time_seconds": 0,
                    "is_verified": True,  # Manually verified
                    "is_active": True    # Ready for feedback collection
                }
                
                insert_query = text("""
                    INSERT INTO expert_profiles (
                        id, user_id, credentials, credential_types, experience_years,
                        specializations, professional_registration_number, organization,
                        location_city, trust_score, feedback_count, feedback_accuracy_rate,
                        average_response_time_seconds, is_verified, is_active,
                        created_at, updated_at
                    ) VALUES (
                        :id, :user_id, :credentials, :credential_types, :experience_years,
                        :specializations, :professional_registration_number, :organization,
                        :location_city, :trust_score, :feedback_count, :feedback_accuracy_rate,
                        :average_response_time_seconds, :is_verified, :is_active,
                        NOW(), NOW()
                    )
                """)
                
                session.execute(insert_query, expert_data)
                session.commit()
                
                print(f"✅ Expert profile created successfully:")
                print(f"   Expert ID: {expert_id}")
                print(f"   Email: {email}")
                print(f"   Credentials: {', '.join(credentials)}")
                print(f"   Experience: {experience_years} years")
                print(f"   Trust Score: 0.5 (will be optimized by system)")
                
                return expert_id
                
            except Exception as e:
                session.rollback()
                print(f"❌ Error creating expert profile: {e}")
                raise
    
    def list_experts(self) -> None:
        """List all expert profiles."""
        
        with Session(self.engine) as session:
            query = text("""
                SELECT 
                    ep.id,
                    u.email,
                    ep.credentials,
                    ep.experience_years,
                    ep.trust_score,
                    ep.is_verified,
                    ep.is_active,
                    ep.created_at
                FROM expert_profiles ep
                JOIN users u ON ep.user_id = u.id
                ORDER BY ep.created_at DESC
            """)
            
            results = session.execute(query).fetchall()
            
            if not results:
                print("No expert profiles found.")
                return
            
            print("\n📋 Current Expert Profiles:")
            print("-" * 80)
            for row in results:
                status = "✅ Active" if row.is_active else "❌ Inactive"
                verified = "✅ Verified" if row.is_verified else "❌ Not Verified"
                
                print(f"Email: {row.email}")
                print(f"Credentials: {', '.join(row.credentials)}")
                print(f"Experience: {row.experience_years} years")
                print(f"Trust Score: {row.trust_score:.2f}")
                print(f"Status: {status} | {verified}")
                print(f"Created: {row.created_at.strftime('%Y-%m-%d %H:%M')}")
                print("-" * 40)
    
    def update_expert_status(self, email: str, is_active: bool) -> None:
        """Enable or disable expert for feedback collection."""
        
        with Session(self.engine) as session:
            try:
                update_query = text("""
                    UPDATE expert_profiles 
                    SET is_active = :is_active, updated_at = NOW()
                    FROM users
                    WHERE expert_profiles.user_id = users.id 
                    AND users.email = :email
                """)
                
                result = session.execute(update_query, {
                    "email": email,
                    "is_active": is_active
                })
                
                if result.rowcount == 0:
                    print(f"❌ Expert with email {email} not found.")
                    return
                
                session.commit()
                status = "enabled" if is_active else "disabled"
                print(f"✅ Expert {email} {status} successfully.")
                
            except Exception as e:
                session.rollback()
                print(f"❌ Error updating expert status: {e}")
                raise


def main():
    """Command-line interface for expert management."""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Create expert: python create_expert.py create --email expert@email.com --credentials dottore_commercialista --years 15")
        print("  List experts:  python create_expert.py list")
        print("  Enable expert: python create_expert.py enable --email expert@email.com")
        print("  Disable expert: python create_expert.py disable --email expert@email.com")
        return
    
    creator = ExpertCreator()
    command = sys.argv[1]
    
    if command == "create":
        # Parse arguments
        args = {}
        for i in range(2, len(sys.argv), 2):
            if i + 1 < len(sys.argv):
                key = sys.argv[i].lstrip('--')
                value = sys.argv[i + 1]
                args[key] = value
        
        required_args = ['email', 'credentials', 'years']
        for arg in required_args:
            if arg not in args:
                print(f"❌ Missing required argument: --{arg}")
                return
        
        # Convert credentials to list
        credentials = [args['credentials']]
        experience_years = int(args['years'])
        
        # Optional arguments
        specializations = args.get('specializations', '').split(',') if args.get('specializations') else None
        organization = args.get('organization')
        location = args.get('location')
        registration = args.get('registration')
        
        # Create expert
        asyncio.run(creator.create_expert_profile(
            email=args['email'],
            credentials=credentials,
            experience_years=experience_years,
            specializations=specializations,
            organization=organization,
            location_city=location,
            registration_number=registration
        ))
    
    elif command == "list":
        creator.list_experts()
    
    elif command == "enable":
        email = None
        for i in range(2, len(sys.argv), 2):
            if sys.argv[i] == '--email' and i + 1 < len(sys.argv):
                email = sys.argv[i + 1]
                break
        
        if not email:
            print("❌ Missing required argument: --email")
            return
        
        creator.update_expert_status(email, True)
    
    elif command == "disable":
        email = None
        for i in range(2, len(sys.argv), 2):
            if sys.argv[i] == '--email' and i + 1 < len(sys.argv):
                email = sys.argv[i + 1]
                break
        
        if not email:
            print("❌ Missing required argument: --email")
            return
        
        creator.update_expert_status(email, False)
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()
```

## Expert Management Examples

### Example 1: Senior Tax Professional

```bash
# Create expert profile for senior Dottore Commercialista
python create_expert.py create \
  --email mario.rossi@studiofiscale.it \
  --credentials dottore_commercialista \
  --years 20 \
  --specializations "fiscale,iva,societario" \
  --organization "Studio Fiscale Rossi & Associati" \
  --location "Milano" \
  --registration "DC-MI-12345"
```

### Example 2: CAF Operator

```bash
# Create expert profile for CAF operator
python create_expert.py create \
  --email anna.bianchi@cafsicilia.it \
  --credentials caf_operator \
  --years 8 \
  --specializations "730,unico,isee" \
  --organization "CAF Sicilia" \
  --location "Palermo"
```

### Example 3: Labor Law Consultant

```bash
# Create expert profile for labor consultant
python create_expert.py create \
  --email giuseppe.verdi@consulavoro.com \
  --credentials consulente_lavoro \
  --years 12 \
  --specializations "ccnl,contributi,tfr" \
  --organization "Consult Lavoro SRL" \
  --location "Roma"
```

## Trust Score Management

### Initial Trust Score

All experts start with `trust_score = 0.5` (50%). The system automatically adjusts based on:
- **Quality of feedback provided** (+0.01 per high-quality feedback)
- **Response time performance** (faster responses = higher score)
- **Consistency and accuracy** (tracked over time)

### Trust Score Monitoring

```sql
-- Monitor expert trust scores
SELECT 
    u.email,
    ep.trust_score,
    ep.feedback_count,
    ep.feedback_accuracy_rate,
    ep.average_response_time_seconds
FROM expert_profiles ep
JOIN users u ON ep.user_id = u.id
WHERE ep.is_active = true
ORDER BY ep.trust_score DESC;
```

### Trust Score Thresholds

- **Minimum for feedback**: 0.7 (70%)
- **High trust expert**: 0.85+ (85%+)
- **System default**: 0.5 (50%)

## Expert Status Management

### Enable/Disable Experts

```bash
# Enable expert for feedback collection
python create_expert.py enable --email expert@email.com

# Disable expert (temporarily suspend)
python create_expert.py disable --email expert@email.com
```

### Check Expert Status

```bash
# List all experts and their status
python create_expert.py list
```

## Quality Monitoring

### Expert Performance Metrics

```sql
-- Expert performance dashboard
SELECT 
    u.email,
    ep.credentials[1] as primary_credential,
    ep.trust_score,
    ep.feedback_count,
    ep.feedback_accuracy_rate,
    ROUND(ep.average_response_time_seconds / 60.0, 1) as avg_response_minutes,
    ep.created_at::date as expert_since
FROM expert_profiles ep
JOIN users u ON ep.user_id = u.id
WHERE ep.is_active = true
ORDER BY ep.trust_score DESC, ep.feedback_count DESC;
```

### Expert Feedback Analytics

```sql
-- Recent expert feedback summary
SELECT 
    u.email,
    COUNT(ef.id) as recent_feedback_count,
    AVG(ef.confidence_score) as avg_confidence,
    ROUND(AVG(ef.time_spent_seconds / 60.0), 1) as avg_time_minutes
FROM expert_profiles ep
JOIN users u ON ep.user_id = u.id
JOIN expert_feedback ef ON ef.expert_id = ep.id
WHERE ef.feedback_timestamp >= NOW() - INTERVAL '30 days'
GROUP BY u.email, ep.id
ORDER BY recent_feedback_count DESC;
```

## Troubleshooting

### Common Issues

#### Expert Cannot Provide Feedback
1. Check if expert is active: `is_active = true`
2. Check if expert is verified: `is_verified = true`
3. Check trust score: must be ≥ 0.7
4. Verify user account exists and is linked correctly

#### Trust Score Not Updating
1. Check if feedback is being processed successfully
2. Verify expert is providing feedback with confidence scores
3. Check system logs for feedback processing errors
4. Ensure feedback processing completes within 30 seconds

#### Expert Profile Creation Fails
1. Verify user account exists first
2. Check credential values match valid types
3. Ensure all required fields are provided
4. Check database connection and permissions

### Debug Commands

```bash
# Check expert's user account
psql -d pratikoai -c "SELECT * FROM users WHERE email = 'expert@email.com';"

# Check expert profile details
psql -d pratikoai -c "SELECT * FROM expert_profiles WHERE user_id = 'uuid-here';"

# Check recent expert feedback
psql -d pratikoai -c "SELECT * FROM expert_feedback WHERE expert_id = 'uuid-here' ORDER BY feedback_timestamp DESC LIMIT 5;"
```

## Security Considerations

### Data Protection
- Expert personal data is protected under GDPR
- Professional registration numbers should be verified but not publicly exposed
- Trust scores and performance metrics are for internal system use only

### Access Control
- Only authorized administrators should create expert profiles
- Database access should be restricted and logged
- Expert management operations should be audited

### Verification Requirements
- Professional credentials must be verified with Italian authorities
- Regular re-verification of active expert status recommended
- Suspicious feedback patterns should be investigated

---

## Quick Reference

### Create Expert Checklist
- [ ] User account exists
- [ ] Professional credentials verified
- [ ] Registration number confirmed
- [ ] Experience years validated
- [ ] Specializations documented
- [ ] Expert profile created with correct data
- [ ] Expert status set to active and verified
- [ ] Trust score monitoring enabled

### Maintenance Tasks
- [ ] Monthly review of expert performance metrics
- [ ] Quarterly trust score analysis
- [ ] Annual re-verification of professional credentials
- [ ] Regular monitoring of feedback quality and system performance

This guide provides everything needed to manually manage expert profiles in the PratikoAI system. The combination of SQL commands and Python scripts makes expert management straightforward while maintaining proper validation and security controls.