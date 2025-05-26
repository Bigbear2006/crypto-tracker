all: run

env:
	@if [ ! -f .env ]; then \
        echo "Creating .env from .env.example"; \
        cat .env.example >> .env; \
    else \
        echo ".env already exists."; \
    fi

run:
	docker-compose up --build -d

restart:
	docker-compose restart bot

rebuild:
	docker-compose up --build -d --no-deps bot

logs:
	docker-compose logs -f bot

migrate:
	docker-compose exec django python manage.py makemigrations
	docker-compose exec django python manage.py migrate

admin:
	docker-compose exec django python manage.py createsuperuser

shell:
	docker-compose exec django python manage.py shell

load:
	docker-compose exec django python manage.py loaddata data.json

dump:
	docker-compose exec django python manage.py dumpdata -o data.json --indent 2

lint:
	ruff format
	ruff check --fix
	ruff format
