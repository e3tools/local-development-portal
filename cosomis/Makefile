pip-install:
	pip install --upgrade pip pip-tools
	pip-sync requirements.txt

server:
	python manage.py migrate && python manage.py runserver

black:
	python -m black cosomis

generate-translations:
	python manage.py makemessages -a --ignore=venv --ignore=collected_static --ignore=node_modules
	python manage.py compilemessages --ignore venv

# Once per clone: register the merge drivers declared in ../.gitattributes
# (gettext catalogs keep the current branch's translations on merge).
setup-git:
	git config merge.po-keep-current.name "gettext .po: keep current branch translations, add new entries"
	git config merge.po-keep-current.driver "cosomis/scripts/git-merge-po.sh %O %A %B %P"
	git config merge.mo-keep-current.name "compiled .mo: keep current branch, recompile after merge"
	git config merge.mo-keep-current.driver true