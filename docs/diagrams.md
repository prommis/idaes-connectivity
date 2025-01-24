---
myst:
  substitutions:
    proj: 'IDAES Connectivity Tool'
---
# Making diagrams

Formatting of connectivity information as a diagram relies on external tools.
While this does require an extra step to install and run these tools, it also provides flexibility and leverages the full power of the tools' user communities.

Below are links an instructions for the supported tools, [](mermaid-tool) and [](d2-tool).
Both tools do roughly the same thing: create diagrams from text, with automatic layout. Mermaid, written in JavaScript, has an online editor and built-in support in GitHub and Jupyter notebooks whereas D2, written in Go, has more flexible layout options and is easier to use in the console.

(mermaid-tool)=
## Mermaid
[Mermaid](https://mermaid.js.org/) describes itself as a "JavaScript based diagramming and charting tool that renders Markdown-inspired text definitions to create and modify diagrams dynamically".
The {{ proj }} can create Mermaid text definitions and also has a convenience function to help render Mermaid diagrams inside a Jupyter Notebook.

### Generate text definition
For example, to generate Mermaid text from  connectivity data in the CSV file *model_conn.csv*, 
you could run:

```
idaes-conn --to mermaid model_conn.csv -O "-"
```

This will print the text definition of the diagram to the console.

### Generate diagram

#### Jupyter / GitHub

You could then paste the output into a Jupyter Notebook markdown cell, or GitHub markdown page, like this:

:::{code}
```mermaid
<PASTE TEXT HERE>
```
:::

#### Online Editor

You could also load these diagrams into the online [Mermaid Live Editor](https://mermaid.live/).

#### Console
If you want to generate the diagram locally, and are willing and able to install NodeJS packages on your machine, then follow these instructions:

First install the mermaid-cli with the [Node Package Manager](https://www.npmjs.com/) (install that first if you don't have it):
```
npm install @mermaid-js/mermaid-cli
```
This will install wherever you ran the command. Make sure you run the next commands in the same directory.
Next, paste the following into a script we will call `run-mermaid.js`:
```
const { run } = await import("@mermaid-js/mermaid-cli");
const input_file = process.argv[2];
const output_file = process.argv[3];
console.log("Generating " + output_file + " from " + input_file);
await run(input_file, output_file);
```

An optional but useful step to avoid some warnings: edit the *package.json* file (this was created when you did the `npm install` command) and add a line at the top.
```
{
   "type": "module",
   # .. rest of file ..
}
```

Finally, you can convert a Mermaid diagram to an SVG (Scalable Vector Graphics image) file with this command:
```
node run-mermaid.js <INPUT.mmd> <OUTPUT.svg>
```


(d2-tool)=
## D2
[Declarative Diagramming (D2)](https://d2lang.com/) describes itself as "A modern language that turns text to diagrams".
Like Mermaid, D2 generates a SVG diagram from a simple text description.

### Generate text definition
For example, to generate D2 text from  connectivity data in the CSV file *model_conn.csv*, 
you could run:
```
idaes-conn --to d2 model_conn.csv -O model_conn.d2
```

This will print the text definition of the diagram to the file *model_conn.d2*

### Generate diagram

To generate the diagram, [install D2 on your computer](https://d2lang.com/tour/install) and then run the `d2` command-line interface (CLI) with the file you generated above as input:
```
d2 model_conn.d2 model_conn.svg
```

There are numerous options to the `d2` CLI that can help modify layout and style, as well as the program behavior. For example, specifying an output file with ".png" as the suffix will generate a PNG image. Run `d2 -h` to see them and/or visit the documentation on the website.

```{note}
Unlike Mermaid, D2 does not have an online editor or Jupyter integration. On the other hand, generating diagrams locally is straightforward.
```