
## The Lava Framework FAQ

### General Questions

#### Retrospectively adding Jupyter notebook support

If Jupyter support was not requested when the project was originally created
using cookiecutter, it can be enabled afterwards using the following process:

```bash
# Got to project root
cd  <PROJECT-ROOT>

# Add jupyter to requirements file
echo jupyter >> etc/requirements.txt

# Install jupyter support
make init
```

#### Retrospectively adding lava libraries

If the lava libraries were not requested when the project was originally created
using cookiecutter, they can be added afterwards using the following process:

```bash
# Got to project root
cd  <PROJECT-ROOT>

# Add lava to requirements file
echo jinlava >> etc/requirements.txt

# Install
make init
```
