NEW_APP_COMPOSE_TEMPLATE = """version: '3'
services:
  {service_name}:
    image: "{base_image}"
    restart: always

"""
