IF EXIST dist (rmdir dist /s /q)
py setup.py sdist
py -m twine upload dist/*
rmdir dist /s /q
rmdir supercache.egg-info /s /q