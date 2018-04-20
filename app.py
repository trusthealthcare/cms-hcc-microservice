#!/usr/bin/env python3
import connexion
import logging
from injector import Binder
from flask_injector import FlaskInjector
from connexion.resolver import RestyResolver
from services.raf import RafCalculator

# Setup the binding for the raf calculator
def configure(binder: Binder) -> Binder:
    binder.bind(
        RafCalculator,
        RafCalculator()
    )

# Logging config




if __name__ == '__main__':

	logging.basicConfig(level=logging.INFO)
	
	app = connexion.App(__name__, specification_dir='swagger/')
	app.add_api('raf.yaml', resolver=RestyResolver('api'))
	FlaskInjector(app=app.app, modules=[configure])
	app.run(port=8080)
