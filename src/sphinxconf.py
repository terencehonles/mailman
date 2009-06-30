# Sphinx documentation configuration file.
def setup(app):
    # hack the 'exclude_trees' configuration value so that our bounce examples
    # aren't interpreted as documentation.
    app.config.config_values['exclude_trees'][0].extend([
        'tests/bounces',
        'templates',
        ])
