
function getParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

const file = getParam("file") || "PI3K_TCGA.json";
const highlighted = (getParam("highlighted") || "").split(",");

document.getElementById("status").innerText = `Pathway: ${file} | Highlighted: ${highlighted.join(", ")}`;

fetch("pathways/" + file)
  .then((res) => res.json())
  .then((data) => {
    const cy = cytoscape({
      container: document.getElementById("cy"),
      elements: data.elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "#999",
            label: "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "color": "#fff",
            "font-size": 10,
            "width": "label",
            "height": "label",
            "padding": "5px",
            "shape": "roundrectangle",
          },
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#ccc",
            "target-arrow-color": "#ccc",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: ".highlighted",
          style: {
            "background-color": "#f00",
            "border-width": 2,
            "border-color": "#000",
          },
        },
      ],
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: 10,
      },
    });

    cy.nodes().forEach((node) => {
      if (highlighted.includes(node.data("id"))) {
        node.addClass("highlighted");
      }
    });
  })
  .catch((err) => {
    document.getElementById("status").innerText = "Failed to load pathway JSON.";
    console.error(err);
  });
