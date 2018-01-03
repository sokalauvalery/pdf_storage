import configparser

config = configparser.ConfigParser()
config.read('config.ini')

constants = config['DEFAULT']