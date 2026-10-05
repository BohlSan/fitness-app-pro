from sqlalchemy.orm import registry

# Todos los modelos se registran acá con @mapper_registry.mapped
mapper_registry = registry()

# Metadata: mantiene la información de las tablas de los modelos
metadata = mapper_registry.metadata
