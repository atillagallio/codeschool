from invoke import run, task

# python-boilerplate tasks
from python_boilerplate.tasks import bump_version


# Add your tasks in here
# This task can be executed with ``invoke build --docs``
@task
def build(no_docs=False):
    """
    Build python package and docs
    """

    run("python setup.py build")
    if not no_docs:
        run("python setup.py build_sphinx")
        
@task
def migrate(make=False, hard_reset=False):
    """
    Run django manage.py migrate command.
    """
    
    if hard_reset:
        run("rm db/db.sqlite3")
    if make:
        run("python src/manage.py makemigrations")
    run("python src/manage.py migrate")


@task
def rmmigrations(keep_data=False, fake=False):
    """
    Remove all migration files. If --keep-data is set, it does not remove
    migrations named as XXXX_data_*.py.
    """

    import os
    import re

    regex = re.compile(r'^[0-9]{4}_\w+.py$')

    def is_migration(path):
        return len(path) >= 4 and path[:4].isdigit() and path.endswith('.py')

    for dir, subdirs, files in os.walk(os.getcwd()):
        if os.path.basename(dir) == 'migrations':
            migrations = [f for f in files if regex.match(f)]
            for f in migrations:
                path = os.path.join(dir, f)
                if keep_data and f[5:].startswith('initial_data'):
                    continue

                print('removing %s' % path, end='')
                if not fake:
                    os.unlink(path)
                    print(' ..OK')
                else:
                    print()


@task
def runserver():
    """
    Executes the runserver command.
    """

    run('python src/manage.py runserver')