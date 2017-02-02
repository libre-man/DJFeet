setup:
	pip3 install --upgrade numpy
	pip3 install -r requirements.txt
	python3 setup.py install

travis_setup:
	pip install --upgrade pip setuptools wheel
	pip install --only-binary=scipy scipy
	pip install -r requirements.txt
	pip install .

clean:
	-rm -r /tmp/sdaas

test_setup:
	-make clean
	mkdir /tmp/sdaas

test_local:
	-mkdir /tmp/sdaas
	pytest -v  tests

test:
	make test_setup
	pytest -v  tests --runslow

style:
	find dj_feet tests -name \[a-zA-Z_]*.py -exec pep8 --ignore=E402 {} +

coverage_local:
	pytest -v --cov-config=.coveragerc --cov-report term-missing --cov=dj_feet tests/

coverage:
	make test_setup
	pytest -v --cov-config=.coveragerc --cov-report term-missing --cov=dj_feet --runslow tests/
