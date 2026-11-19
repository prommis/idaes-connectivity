# Iconify package build

This directory converts the SVG equipment illustrations in
`idaes_connectivity/images` into an IconifyJSON npm package. The illustrations
retain their fixed color palette.

```powershell
npm install
npm run build
```

The generated package is written to `dist/package`. Build output and
`node_modules` are intentionally not committed.

The build performs strict SVG validation, removes editor metadata, optimizes
the vector data, and fails if any source icon cannot be converted. It does not
publish or register the generated package.
