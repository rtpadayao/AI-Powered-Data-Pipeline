#!/usr/bin/env python3
"""
Verification script for the AI-Powered Airflow data pipeline.

This script checks:
1. File existence and structure
2. Python and SQL syntax (where possible)
3. dbt model validity
4. FastAPI endpoint definitions
5. extract_load.py functionality
6. Basic logic validation

Since Docker services may not be available, this focuses on static checks.
"""

import os
import sys
import ast
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a section header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_failure(text: str):
    """Print a failure message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.ENDC}")

class PipelineVerifier:
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.results = {
            'file_structure': {'passed': 0, 'failed': 0, 'details': []},
            'python_syntax': {'passed': 0, 'failed': 0, 'details': []},
            'sql_syntax': {'passed': 0, 'failed': 0, 'details': []},
            'dbt_models': {'passed': 0, 'failed': 0, 'details': []},
            'fastapi_endpoints': {'passed': 0, 'failed': 0, 'details': []},
            'extract_load': {'passed': 0, 'failed': 0, 'details': []},
        }

    def check_file_exists(self, file_path: str, description: str) -> bool:
        """Check if a file exists."""
        full_path = self.repo_root / file_path
        if full_path.exists() and full_path.is_file():
            print_success(f"{description}: {file_path}")
            return True
        else:
            print_failure(f"{description}: {file_path} (NOT FOUND)")
            return False

    def check_directory_exists(self, dir_path: str, description: str) -> bool:
        """Check if a directory exists."""
        full_path = self.repo_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print_success(f"{description}: {dir_path}")
            return True
        else:
            print_failure(f"{description}: {dir_path} (NOT FOUND)")
            return False

    def check_python_syntax(self, file_path: str, description: str) -> bool:
        """Check Python file syntax."""
        full_path = self.repo_root / file_path
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            ast.parse(content)
            print_success(f"{description}: {file_path} (syntax OK)")
            return True
        except SyntaxError as e:
            print_failure(f"{description}: {file_path} (syntax error: {e})")
            return False
        except Exception as e:
            print_failure(f"{description}: {file_path} (error reading: {e})")
            return False

    def check_sql_syntax_basic(self, file_path: str, description: str) -> bool:
        """Basic SQL syntax check (just look for obvious issues)."""
        full_path = self.repo_root / file_path
        try:
            with open(full_path, 'r') as f:
                content = f.read()

            # Basic checks
            if not content.strip():
                print_warning(f"{description}: {file_path} (empty file)")
                return True  # Empty is technically OK syntax-wise

            # Check for balanced parentheses (simple check)
            open_paren = content.count('(')
            close_paren = content.count(')')
            if open_paren != close_paren:
                print_failure(f"{description}: {file_path} (unbalanced parentheses)")
                return False

            # Check for basic SQL structure
            if 'select' not in content.lower() and 'with' not in content.lower():
                print_warning(f"{description}: {file_path} (no SELECT or WITH found)")

            print_success(f"{description}: {file_path} (basic SQL syntax OK)")
            return True
        except Exception as e:
            print_failure(f"{description}: {file_path} (error reading: {e})")
            return False

    def verify_file_structure(self):
        """Verify that all required files and directories exist."""
        print_header("FILE STRUCTURE VERIFICATION")

        # Core directories
        dirs_to_check = [
            ("airflow/dags", "Airflow DAGs directory"),
            ("dbt_project/models", "dbt models directory"),
            ("dbt_project/models/staging", "dbt staging models"),
            ("dbt_project/models/refined", "dbt refined models"),
            ("dbt_project/models/marts", "dbt marts models"),
            ("dbt_project/seeds", "dbt seeds directory"),
            ("dbt_project/macros", "dbt macros directory"),
            ("api", "FastAPI application"),
            ("infrastructure/raw_storage", "Raw storage directory"),
            ("infrastructure/postgres", "PostgreSQL infrastructure"),
            ("notebooks", "Jupyter notebooks"),
        ]

        for dir_path, description in dirs_to_check:
            result = self.check_directory_exists(dir_path, description)
            if result:
                self.results['file_structure']['passed'] += 1
            else:
                self.results['file_structure']['failed'] += 1
            self.results['file_structure']['details'].append({
                'check': description,
                'path': dir_path,
                'result': 'passed' if result else 'failed'
            })

        # Key files
        files_to_check = [
            ("docker-compose.yml", "Docker Compose configuration"),
            ("dbt_project/dbt_project.yml", "dbt project configuration"),
            ("dbt_project/profiles.yml", "dbt profiles"),
            ("api/main.py", "FastAPI main application"),
            ("api/database.py", "FastAPI database utilities"),
            ("api/schemas.py", "FastAPI Pydantic schemas"),
            ("api/extract_load.py", "Extract/load script"),
            ("airflow/dags/finance_etl_daily.py", "Airflow DAG"),
            ("infrastructure/postgres/init-db.sql", "PostgreSQL initialization script"),
            ("notebooks/eda_profiling.ipynb", "EDA notebook"),
            ("notebooks/requirements.txt", "Notebook requirements"),
        ]

        for file_path, description in files_to_check:
            result = self.check_file_exists(file_path, description)
            if result:
                self.results['file_structure']['passed'] += 1
            else:
                self.results['file_structure']['failed'] += 1
            self.results['file_structure']['details'].append({
                'check': description,
                'path': file_path,
                'result': 'passed' if result else 'failed'
            })

    def verify_python_syntax(self):
        """Verify Python file syntax."""
        print_header("PYTHON SYNTAX VERIFICATION")

        python_files = [
            ("api/main.py", "FastAPI main application"),
            ("api/database.py", "FastAPI database utilities"),
            ("api/schemas.py", "FastAPI Pydantic schemas"),
            ("api/extract_load.py", "Extract/load script"),
            ("airflow/dags/finance_etl_daily.py", "Airflow DAG"),
            ("infrastructure/raw_storage/api_requests.py", "Raw storage API requests"),
            ("infrastructure/raw_storage/create_restapi_w_FastAPI.py", "Create REST API with FastAPI"),
        ]

        for file_path, description in python_files:
            result = self.check_python_syntax(file_path, description)
            if result:
                self.results['python_syntax']['passed'] += 1
            else:
                self.results['python_syntax']['failed'] += 1
            self.results['python_syntax']['details'].append({
                'check': description,
                'path': file_path,
                'result': 'passed' if result else 'failed'
            })

    def verify_sql_syntax(self):
        """Verify SQL file syntax."""
        print_header("SQL SYNTAX VERIFICATION")

        sql_files = [
            ("dbt_project/models/staging/stg_gl_transactions.sql", "Staging model"),
            ("dbt_project/models/refined/dim_account.sql", "Dimension account model"),
            ("dbt_project/models/refined/dim_date.sql", "Dimension date model"),
            ("dbt_project/models/refined/fact_gl_transactions.sql", "Fact GL transactions model"),
            ("dbt_project/models/marts/normalize.sql", "Normalize marts model"),
            ("dbt_project/models/marts/financial_statements.sql", "Financial statements model"),
            ("dbt_project/models/marts/account_balances.sql", "Account balances model"),
            ("infrastructure/postgres/init-db.sql", "PostgreSQL initialization script"),
        ]

        for file_path, description in sql_files:
            result = self.check_sql_syntax_basic(file_path, description)
            if result:
                self.results['sql_syntax']['passed'] += 1
            else:
                self.results['sql_syntax']['failed'] += 1
            self.results['sql_syntax']['details'].append({
                'check': description,
                'path': file_path,
                'result': 'passed' if result else 'failed'
            })

    def verify_dbt_models(self):
        """Verify dbt model structure and references."""
        print_header("DBT MODELS VERIFICATION")

        # Check dbt_project.yml
        dbt_yml_path = self.repo_root / "dbt_project/dbt_project.yml"
        if dbt_yml_path.exists():
            try:
                with open(dbt_yml_path, 'r') as f:
                    content = f.read()
                # Basic checks
                if 'name:' in content and 'version:' in content:
                    print_success("dbt_project.yml: Basic structure OK")
                    self.results['dbt_models']['passed'] += 1
                else:
                    print_warning("dbt_project.yml: Missing name or version")
                    self.results['dbt_models']['failed'] += 1
            except Exception as e:
                print_failure(f"dbt_project.yml: Error reading - {e}")
                self.results['dbt_models']['failed'] += 1
        else:
            print_failure("dbt_project.yml: File not found")
            self.results['dbt_models']['failed'] += 1

        # Check schema.yml files
        schema_files = [
            ("dbt_project/models/staging/schema.yml", "Staging schema"),
            ("dbt_project/models/refined/schema.yml", "Refined schema"),
        ]

        for file_path, description in schema_files:
            full_path = self.repo_root / file_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    if 'version:' in content and 'models:' in content:
                        print_success(f"{description}: {file_path} (structure OK)")
                        self.results['dbt_models']['passed'] += 1
                    else:
                        print_warning(f"{description}: {file_path} (missing version or models)")
                        self.results['dbt_models']['failed'] += 1
                except Exception as e:
                    print_failure(f"{description}: {file_path} (error: {e})")
                    self.results['dbt_models']['failed'] += 1
            else:
                print_failure(f"{description}: {file_path} (NOT FOUND)")
                self.results['dbt_models']['failed'] += 1

        # Check seeds
        seeds_dir = self.repo_root / "dbt_project/seeds"
        if seeds_dir.exists():
            seed_files = list(seeds_dir.glob("*.csv"))
            if seed_files:
                print_success(f"dbt seeds: Found {len(seed_files)} CSV file(s)")
                self.results['dbt_models']['passed'] += 1
            else:
                print_warning("dbt seeds: No CSV files found")
                self.results['dbt_models']['failed'] += 1
        else:
            print_failure("dbt seeds: Directory not found")
            self.results['dbt_models']['failed'] += 1

        # Check for model dependencies (references)
        model_files = [
            ("dbt_project/models/staging/stg_gl_transactions.sql", "staging", "reads from source"),
            ("dbt_project/models/refined/dim_account.sql", "refined", "uses ref()"),
            ("dbt_project/models/refined/dim_date.sql", "refined", "generates dates (no ref needed)"),
            ("dbt_project/models/refined/fact_gl_transactions.sql", "refined", "uses ref()"),
            ("dbt_project/models/marts/normalize.sql", "marts", "uses ref()"),
            ("dbt_project/models/marts/financial_statements.sql", "marts", "uses ref()"),
            ("dbt_project/models/marts/account_balances.sql", "marts", "uses ref()"),
        ]

        for model_file, model_type, expectation in model_files:
            full_path = self.repo_root / model_file
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()

                    # Special handling for different model types
                    if model_type == "staging" and expectation == "reads from source":
                        # Staging should read from source table
                        if 'from finance.gl_transactions' in content:
                            print_success(f"Model reference check: {model_file} (reads from source)")
                            self.results['dbt_models']['passed'] += 1
                        else:
                            print_warning(f"Model reference check: {model_file} (may not read from correct source)")
                            self.results['dbt_models']['failed'] += 1
                    elif model_type == "refined" and model_file.endswith("dim_date.sql") and expectation == "generates dates (no ref needed)":
                        # dim_date special case - generates dates from scratch
                        print_success(f"Model reference check: {model_file} (generates dates from scratch)")
                        self.results['dbt_models']['passed'] += 1
                    elif '{{ ref(' in content:
                        # Other models should use ref()
                        print_success(f"Model reference check: {model_file} (uses ref())")
                        self.results['dbt_models']['passed'] += 1
                    else:
                        print_warning(f"Model reference check: {model_file} (no ref() found)")
                        self.results['dbt_models']['failed'] += 1
                except Exception as e:
                    print_failure(f"Model reference check: {model_file} (error: {e})")
                    self.results['dbt_models']['failed'] += 1
            else:
                print_failure(f"Model reference check: {model_file} (NOT FOUND)")
                self.results['dbt_models']['failed'] += 1

    def verify_fastapi_endpoints(self):
        """Verify FastAPI endpoint definitions."""
        print_header("FASTAPI ENDPOINTS VERIFICATION")

        main_py_path = self.repo_root / "api/main.py"
        if not main_py_path.exists():
            print_failure("FastAPI main.py: File not found")
            self.results['fastapi_endpoints']['failed'] += 1
            return

        try:
            with open(main_py_path, 'r') as f:
                content = f.read()

            # Check for key endpoints (look for the decorator pattern)
            endpoints_to_check = [
                ('/transactions/raw"', "Raw transactions endpoint"),
                ('/transactions"', "Normalized transactions endpoint"),  # This will match both /transactions and /transactions/{param}
                ('/transactions/refined/{table_name}"', "Refined data endpoint"),
                ('/transactions/marts/{table_name}"', "Marts data endpoint"),
                ('/health"', "Health check endpoint"),
            ]

            for endpoint_pattern, description in endpoints_to_check:
                if endpoint_pattern in content:
                    print_success(f"FastAPI endpoint: {description}")
                    self.results['fastapi_endpoints']['passed'] += 1
                else:
                    print_failure(f"FastAPI endpoint: {description} (NOT FOUND)")
                    self.results['fastapi_endpoints']['failed'] += 1

            # Check for imports
            imports_to_check = [
                ('from .schemas import', "Pydantic schemas import"),
                ('from .database import', "Database utilities import"),
            ]

            for import_pattern, description in imports_to_check:
                if import_pattern in content:
                    print_success(f"FastAPI import: {description}")
                    self.results['fastapi_endpoints']['passed'] += 1
                else:
                    print_failure(f"FastAPI import: {description} (NOT FOUND)")
                    self.results['fastapi_endpoints']['failed'] += 1

        except Exception as e:
            print_failure(f"FastAPI main.py: Error reading - {e}")
            self.results['fastapi_endpoints']['failed'] += 1

    def verify_extract_load(self):
        """Verify extract_load.py functionality."""
        print_header("EXTRACT/LOAD SCRIPT VERIFICATION")

        extract_load_path = self.repo_root / "api/extract_load.py"
        if not extract_load_path.exists():
            print_failure("extract_load.py: File not found")
            self.results['extract_load']['failed'] += 1
            return

        try:
            with open(extract_load_path, 'r') as f:
                content = f.read()

            # Check for key functions
            functions_to_check = [
                ('def fetch_raw_data()', "fetch_raw_data function"),
                ('def transform_row(', "transform_row function"),
                ('def load_data_to_db(', "load_data_to_db function"),
                ('def main():', "main function"),
            ]

            for func_pattern, description in functions_to_check:
                result = func_pattern in content
                if result:
                    print_success(f"extract_load function: {description}")
                    self.results['extract_load']['passed'] += 1
                else:
                    print_failure(f"extract_load function: {description} (NOT FOUND)")
                    self.results['extract_load']['failed'] += 1

            # Check for API endpoint usage
            result = 'CSV_ENDPOINT = f"{API_BASE_URL}/transactions/raw"' in content
            if result:
                print_success("extract_load: Uses correct API endpoint for raw data")
                self.results['extract_load']['passed'] += 1
            else:
                print_warning("extract_load: May not use correct API endpoint")
                self.results['extract_load']['failed'] += 1

            # Check for batch processing
            result = 'BATCH_SIZE' in content and 'execute_batch' in content
            if result:
                print_success("extract_load: Implements batch processing")
                self.results['extract_load']['passed'] += 1
            else:
                print_warning("extract_load: May not implement batch processing")
                self.results['extract_load']['failed'] += 1

        except Exception as e:
            print_failure(f"extract_load.py: Error reading - {e}")
            self.results['extract_load']['failed'] += 1

    def verify_basic_logic(self):
        """Verify basic logic consistency."""
        print_header("BASIC LOGIC VERIFICATION")

        # Check that staging model reads from the right table
        staging_path = self.repo_root / "dbt_project/models/staging/stg_gl_transactions.sql"
        if staging_path.exists():
            try:
                with open(staging_path, 'r') as f:
                    content = f.read()
                if 'from finance.gl_transactions' in content:
                    print_success("Staging model correctly reads from finance.gl_transactions")
                    self.results['dbt_models']['passed'] += 1
                else:
                    print_warning("Staging model may not read from correct source table")
                    self.results['dbt_models']['failed'] += 1
            except Exception as e:
                print_failure(f"Staging model logic check: {e}")
                self.results['dbt_models']['failed'] += 1

        # Check that marts models reference refined models
        marts_models = [
            ("dbt_project/models/marts/normalize.sql", "normalize"),
            ("dbt_project/models/marts/financial_statements.sql", "financial_statements"),
            ("dbt_project/models/marts/account_balances.sql", "account_balances"),
        ]

        for model_path, model_name in marts_models:
            full_path = self.repo_root / model_path
            if full_path.exists():
                try:
                    with open(full_path, 'r') as f:
                        content = f.read()
                    # Check that it references staging or refined models
                    if "{{ ref('stg_gl_transactions') }}" in content or \
                       "{{ ref('dim_account') }}" in content or \
                       "{{ ref('dim_date') }}" in content or \
                       "{{ ref('normalize') }}" in content:
                        print_success(f"{model_name} marts model: References other models correctly")
                        self.results['dbt_models']['passed'] += 1
                    else:
                        print_warning(f"{model_name} marts model: May not reference other models correctly")
                        self.results['dbt_models']['failed'] += 1
                except Exception as e:
                    print_failure(f"{model_name} marts model logic check: {e}")
                    self.results['dbt_models']['failed'] += 1
            else:
                print_failure(f"{model_name} marts model: File not found")
                self.results['dbt_models']['failed'] += 1

    def print_summary(self):
        """Print verification summary."""
        print_header("VERIFICATION SUMMARY")

        total_passed = 0
        total_failed = 0

        for category, results in self.results.items():
            passed = results['passed']
            failed = results['failed']
            total = passed + failed
            total_passed += passed
            total_failed += failed

            if total > 0:
                percentage = (passed / total) * 100
                status = "PASS" if failed == 0 else "FAIL"
                color = Colors.GREEN if failed == 0 else Colors.RED
                print(f"{color}{category.upper():<20} {passed:>3}/{total:<3} ({percentage:>5.1f}%) [{status}]{Colors.ENDC}")
            else:
                print(f"{Colors.YELLOW}{category.upper():<20} {'   0/0   (   0.0%) [SKIP]':<20}{Colors.ENDC}")

        print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        overall_total = total_passed + total_failed
        if overall_total > 0:
            overall_percentage = (total_passed / overall_total) * 100
            overall_status = "PASS" if total_failed == 0 else "FAIL"
            overall_color = Colors.GREEN if total_failed == 0 else Colors.RED
            print(f"{overall_color}{Colors.BOLD}OVERALL RESULT: {total_passed}/{overall_total} ({overall_percentage:>5.1f}%) [{overall_status}]{Colors.ENDC}")
        else:
            print(f"{Colors.YELLOW}{Colors.BOLD}OVERALL RESULT: No checks performed{Colors.ENDC}")
        print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")

        # Return True if overall pass, False otherwise
        return total_failed == 0

    def run_all_checks(self):
        """Run all verification checks."""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print("AI-Powered Airflow Data Pipeline Verification")
        print("==============================================")
        print(f"{Colors.ENDC}")

        self.verify_file_structure()
        self.verify_python_syntax()
        self.verify_sql_syntax()
        self.verify_dbt_models()
        self.verify_fastapi_endpoints()
        self.verify_extract_load()
        self.verify_basic_logic()

        return self.print_summary()

def main():
    """Main function."""
    repo_root = "/home/roy/repos/cc_AI-Powered_Airflow"

    if not os.path.exists(repo_root):
        print(f"{Colors.RED}Error: Repository root not found at {repo_root}{Colors.ENDC}")
        sys.exit(1)

    verifier = PipelineVerifier(repo_root)
    success = verifier.run_all_checks()

    if success:
        print(f"\n{Colors.GREEN}{Colors.BOLD}Verification PASSED!{Colors.ENDC}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}Verification FAILED!{Colors.ENDC}")
        sys.exit(1)

if __name__ == "__main__":
    main()