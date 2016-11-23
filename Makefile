setup:
	pip3 install --upgrade numpy
	pip3 install -r requirements.txt
	python3 setup.py install

test:
	pytest -v  tests

style:
	find dj_feet tests -name \[a-zA-Z_]*.py -exec pep8 --ignore=E402 {} +

coverage:
	pytest -v --cov-config=.coveragerc --cov=dj_feet tests/
