.PHONY: all lint format install app db tests unittests

lint:
	- @poetry run flake8
format: 
	- @poetry run black .
install:
	- @poetry install
app:
	- @poetry run start  --config=config/config-base.yaml
db:
	- @poetry run sqlite_web data/db_crypto.db
tests:
	- @poetry run pytest
unittests:
	- @poetry run python -m unittest discover tests