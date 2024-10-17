pip-install:
	pip install --upgrade pip pip-tools
	pip-sync requirements.txt

server:
	python manage.py migrate && python manage.py runserver

black:
	python -m black cosomis

generate-translations:
	python manage.py makemessages -a --no-location
	python manage.py compilemessages --ignore venv