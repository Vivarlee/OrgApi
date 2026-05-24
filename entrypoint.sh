#!/bin/bash

# Apply database migrations
echo "Creating and applying database migrations..."
python manage.py makemigrations departments
python manage.py migrate

# Run tests if specified
if [ "$RUN_TESTS" = "true" ]; then
    echo "Running tests..."
    python manage.py test departments --verbosity=2
    exit $?
fi

# Execute the command passed to docker run
exec "$@"