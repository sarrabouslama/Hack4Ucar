# Hack4Ucar AI Modules

Domain-first AI modules for integrated university management system built with Python + FastAPI.

Powered by **Supabase (PostgreSQL)** with pre-seeded realistic fake data for development and testing.

## Architecture

The application is organized into **5 domain-first modules**:

1. **documents-ingestion** - Shared intake and review workflow for uploaded documents and extracted data
2. **education-research** - Academic performance, enrollment, exams, and research indicators
3. **finance-partnerships-hr** - Budget, partnerships, reports, rankings, HR metrics, contracts, and employment outcomes
4. **environment-infrastructure** - ESG, CO2, energy, recycling, inventory, equipment, and facility health
5. **chatbot-automation** - Cross-domain chatbot actions, optimization workflows, and executive orchestration

## Project Structure

```
Hack4Ucar/
├── app/
│   ├── main.py                  # FastAPI entry point
│   ├── config.py                # Configuration
│   ├── dependencies.py          # Shared dependencies
│   ├── modules/                 # Domain-first modules
│   │   ├── documents_ingestion/
│   │   ├── education_research/
│   │   ├── finance_partnerships_hr/
│   │   ├── environment_infrastructure/
│   │   └── chatbot_automation/
│   ├── shared/                  # Cross-cutting utilities
│   └── core/                    # Core infrastructure
│       ├── models.py            # Base SQLAlchemy models
│       └── database.py          # Database setup
├── scripts/
│   └── seed_db.py              # Database seeding script
├── tests/                       # Testing structure
├── requirements.txt             # Dependencies
├── .env.example                 # Environment template
├── docker-compose.yml           # Container orchestration
└── README.md
```

## Technology Stack

- **Framework**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **ORM**: SQLAlchemy
- **Validation**: Pydantic
- **Data Generation**: Faker (for seeding)

## Quick Start

### Prerequisites
- Python 3.9+
- pip
- PostgreSQL (or Supabase account)

### Installation

```bash
# Clone repository
cd Hack4Ucar

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
```

### Database Setup

#### Option 1: Local PostgreSQL

```bash
# Update .env with your local PostgreSQL credentials
DATABASE_URL=postgresql://postgres:password@localhost:5432/hack4ucar

# Create database
createdb hack4ucar

# Seed with fake data
python -m scripts.seed_db
```

#### Option 2: Supabase (Cloud)

1. Create account at [supabase.com](https://supabase.com)
2. Create new project
3. Copy connection string to `.env`:
   ```
   DATABASE_URL=postgresql://postgres:[PASSWORD]@[PROJECT].supabase.co:5432/postgres
   ```
4. Run seed script:
   ```bash
   python -m scripts.seed_db
   ```

### Running the Application

```bash
# Start development server
python -m uvicorn app.main:app --reload

# Application will be available at http://localhost:8000
# API docs (Swagger): http://localhost:8000/docs
# Alternative docs (ReDoc): http://localhost:8000/redoc
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_documents.py
```

## Database Schema

Each domain module has its own database models:

### Documents Ingestion
- `documents` - Document records with extraction status

### Education & Research
- `students` - Student information
- `courses` - Course offerings
- `enrollments` - Student-course relationships
- `exams` - Exam results and scores
- `research_indicators` - Research metrics

### Finance & HR
- `budgets` - Department budgets
- `partnerships` - Partnership records
- `financial_reports` - Financial statements
- `rankings` - Institution rankings
- `employees` - Employee records
- `contracts` - Employment contracts
- `absenteeism` - Absence records
- `employment_outcomes` - Graduate employment data

### Environment & Infrastructure
- `esg_metrics` - ESG measurements
- `carbon_footprint` - CO2 emissions data
- `energy_consumption` - Energy usage
- `recycling_statistics` - Recycling data
- `inventory_items` - Inventory records
- `equipment` - Equipment inventory
- `facility_health` - Facility condition

### Chatbot & Automation
- `chat_sessions` - Chat sessions
- `chat_messages` - Chat message history
- `automation_actions` - Available actions
- `workflows` - Defined workflows
- `workflow_executions` - Execution history
- `orchestrations` - Cross-domain orchestrations

## API Endpoints

### Documents Ingestion (`/api/v1/documents`)
- `POST /upload` - Upload document
- `GET /documents` - List documents
- `GET /documents/{id}` - Get document details

### Education & Research (`/api/v1/education`)
- `GET /performance/{student_id}` - Student performance
- `GET /enrollment` - Enrollment stats
- `GET /exams` - Exam results
- `GET /research` - Research indicators

### Finance & HR (`/api/v1/finance`)
- `GET /budget` - Budget information
- `GET /partnerships` - Partnership data
- `GET /reports` - Financial reports
- `GET /rankings` - Institution rankings
- `GET /employees` - Employee data
- `GET /hr/contracts` - Employment contracts
- `GET /hr/workload` - Employee workload
- `GET /hr/absenteeism` - Absenteeism data
- `GET /hr/outcomes` - Employment outcomes

### Environment & Infrastructure (`/api/v1/environment`)
- `GET /esg` - ESG metrics
- `GET /carbon` - Carbon footprint
- `GET /energy` - Energy consumption
- `GET /recycling` - Recycling statistics
- `GET /inventory` - Inventory items
- `GET /equipment` - Equipment status
- `GET /facilities` - Facility health

### Chatbot & Automation (`/api/v1/chatbot`)
- `POST /chat` - Chat endpoint
- `POST /actions` - Execute actions
- `GET /workflows` - List workflows
- `POST /workflows/{id}/execute` - Execute workflow
- `GET /orchestration` - Orchestration status

## Development

### Adding a New Endpoint

1. **Add database model** in `modules/{domain}/db_models.py`:
   ```python
   from app.core.models import BaseModel
   from sqlalchemy import Column, String
   
   class MyModel(BaseModel):
       __tablename__ = "my_table"
       field = Column(String(255))
   ```

2. **Add route** in `modules/{domain}/routes.py`:
   ```python
   @router.get("/my-endpoint")
   async def my_endpoint():
       return {"data": "value"}
   ```

3. **Add Pydantic model** in `modules/{domain}/models.py`:
   ```python
   from pydantic import BaseModel
   
   class MySchema(BaseModel):
       field: str
   ```

4. **Add service logic** in `modules/{domain}/services.py`:
   ```python
   class MyService:
       async def get_data(self):
           pass
   ```

5. **Add tests** in `tests/unit/`:
   ```python
   def test_my_endpoint(client):
       response = client.get("/api/v1/my-endpoint")
       assert response.status_code == 200
   ```

### Database Migrations

When you modify database models:

```bash
# The application auto-creates tables on startup
# For production migrations, use Alembic (future enhancement)
```

### Configuration

Environment variables are managed through `.env` file. See `.env.example` for all available options:

- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_URL` - Supabase project URL (optional)
- `SUPABASE_KEY` - Supabase API key (optional)
- `DEBUG` - Debug mode (default: False)
- `CORS_ORIGINS` - CORS allowed origins

## Seeding Data

The `scripts/seed_db.py` script generates realistic fake data for all tables:

```bash
# Run seeding
python -m scripts.seed_db

# Output shows progress
# ✓ Database tables created
# ✓ Documents seeded
# ✓ Education data seeded
# ✓ Finance and HR data seeded
# ✓ Environment data seeded
# ✓ Chatbot and automation data seeded
```

**Generated Data Includes:**
- 10 documents with various statuses
- 20 students with courses, enrollments, and exams
- 15 employees with contracts and HR data
- 8 partnerships and financial reports
- 4 institution rankings
- 5 facilities with equipment and inventory
- Multiple ESG, carbon, and energy metrics
- 5 chat sessions with messages and workflows

All fake data is randomly generated using [Faker](https://faker.readthedocs.io/) library.

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up

# Application will be available at http://localhost:8000
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests
4. Submit a pull request

## License

MIT

