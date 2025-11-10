{% extends 'python.tpl'%}
## Comments magic statement
 {% block codecell %}
 {{  super().replace('get_ipython','#get_ipython') if "get_ipython" in super() else super() }}
 {% endblock codecell %}
