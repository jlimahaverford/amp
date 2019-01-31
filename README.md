* Setup Database:
  1. Create Database: Option (a) or (b)
     1. SQLite: No need to create a database.  Comment out `DATABASE_URL` assignment in `dev-setup.sh`.  After step (ii) the file `app.db` will be created.
     2. PostgreSQL: Visit https://postgresapp.com/ and download postgres and the postgreSQL CLI.  After that create the `amp` database by typing `psql` into bash and then issuin the command `create database amp;`.
  2. Migrate Database: `flask db upgrade` until you reach the current migration (`c6d8e171b6f2, initial_migration`)
* Setup Environment:
  1. Verify python3 installed `which python3`
  2. Create virtual env: `python3 -m venv venv`
  3. `pip install requirements.txt`
* Run Application:
  1. `flask run`
