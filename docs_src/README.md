# Deploying the documentation

The documentation is created and built in the main branch.
Deployment happens from the `docs` branch.
Below is a simple deployment process.

To deploy, first build in this (`docs_src`) directory with:
```
jb build .
```
You can look at / test your docs locally.
When you are satisfied they are ready, check out the `docs` branch.
```
git co docs
```
Copy the built html from `docs_src/_build/html` into `docs/` with
this command (from within the `docs_src` directory):
```
cp -r _build/html/* ../docs
```
Finally, commit and push the built HTML directly into the branch:
```
git commit -am "built docs" && git push --set-upstream upstream docs
```
Don't forget to switch out of this branch before you do more work.
```
git co main
```
