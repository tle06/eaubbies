var rectangles = [
  { name: "all", coordinates: {}, color: "blue" },
  { name: "integer", coordinates: {}, color: "red" },
  { name: "digit", coordinates: {}, color: "green" },
];

var currentRectangleIndex = 0;

function ShowLoader(id, display = "block") {
  var el = document.getElementById(id);
  if (el) el.style.display = display;
}

function HideLoader(id) {
  var el = document.getElementById(id);
  if (el) el.style.display = "none";
}

function ShowErrorMessages(errorid, msg) {
  var el = document.getElementById(errorid);
  el.style.display = "block";
  el.querySelector("p").textContent = msg;
}

function ResetErrorMessages(errorid) {
  var el = document.getElementById(errorid);
  el.style.display = "none";
  var p = el.querySelector("p");
  if (p) p.textContent = "";
}

function EmptyTableBody(bodyid) {
  var tbody = document.getElementById(bodyid);
  tbody.querySelectorAll("tr").forEach(function (r) {
    r.remove();
  });
}

// cache-bust a src so the browser reloads the file
function bustCache(path) {
  return path + "?t=" + Date.now();
}

// Draw the image with rotation on canvas
function drawImageWithRotation(ctx, img, angle, canvas) {
  var rad = (-angle * Math.PI) / 180;
  var cos = Math.abs(Math.cos(rad));
  var sin = Math.abs(Math.sin(rad));
  var newWidth = img.height * sin + img.width * cos;
  var newHeight = img.height * cos + img.width * sin;

  canvas.width = newWidth;
  canvas.height = newHeight;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate(rad);
  ctx.drawImage(img, -img.width / 2, -img.height / 2, img.width, img.height);
  ctx.setTransform(1, 0, 0, 1, 0, 0);

  rectangles.forEach(function (rect) {
    var c = rect.coordinates;
    if (c.x !== undefined) {
      ctx.strokeStyle = rect.color;
      ctx.lineWidth = 2;
      ctx.strokeRect(c.x, c.y, c.width, c.height);
    }
  });
}

// ─── Result rendering ────────────────────────────────────────────────────────

var RESULT_LABELS = {
  total_liters: { label: "Total", icon: "bx-droplet", primary: true },
  left_number: { label: "Integer part", icon: "bx-hash" },
  right_number: { label: "Decimal part", icon: "bx-hash" },
  integer_uom: { label: "Integer UoM", icon: "bx-ruler" },
  decimal_uom: { label: "Decimal UoM", icon: "bx-ruler" },
  main_uom: { label: "Report UoM", icon: "bx-ruler" },
  raw_result: { label: "Raw OCR", icon: "bx-text" },
  raw_result_without_space: { label: "Raw (no space)", icon: "bx-text" },
};

function renderResultCards(result) {
  var container = document.getElementById("result-cards");
  container.innerHTML = "";

  // Primary metric first
  Object.keys(result).forEach(function (key) {
    var meta = RESULT_LABELS[key] || { label: key, icon: "bx-data" };
    var isPrimary = meta.primary;
    var col = document.createElement("div");
    col.className = isPrimary ? "col-md-3 col-6" : "col-md-2 col-6";

    var card = document.createElement("div");
    card.className = isPrimary
      ? "card border-primary h-100 text-center p-3"
      : "card h-100 text-center p-2";

    var icon = document.createElement("i");
    icon.className =
      "bx " +
      meta.icon +
      (isPrimary ? " fs-1 text-primary" : " fs-4 text-secondary");

    var val = document.createElement("div");
    val.className = isPrimary ? "fs-3 fw-bold mt-1" : "fw-semibold mt-1 small";
    val.textContent = result[key];

    var lbl = document.createElement("div");
    lbl.className = "text-muted" + (isPrimary ? "" : " small");
    lbl.textContent = meta.label;

    card.appendChild(icon);
    card.appendChild(val);
    card.appendChild(lbl);
    col.appendChild(card);
    container.appendChild(col);
  });
}

function renderPipelineStrip(source, pipeline, final, ocr) {
  var container = document.getElementById("pipeline-strip");
  container.innerHTML = "";

  var steps = [{ label: "Source", path: source }].concat(pipeline).concat([
    { label: "Final", path: final },
    { label: "OCR", path: ocr },
  ]);

  steps.forEach(function (step) {
    var col = document.createElement("div");
    col.className = "col-md-2 col-4";

    var img = document.createElement("img");
    img.src = bustCache(step.path);
    img.alt = step.label;
    img.className = "img-fluid rounded border";
    img.style.cssText =
      "max-height:130px;object-fit:contain;width:100%;cursor:pointer;";
    img.title = step.label;
    // click to open full-size in new tab
    img.addEventListener("click", function () {
      window.open(bustCache(step.path), "_blank");
    });

    var lbl = document.createElement("p");
    lbl.className = "text-muted small text-center mt-1 mb-0";
    lbl.textContent = step.label;

    col.appendChild(img);
    col.appendChild(lbl);
    container.appendChild(col);
  });
}

// ─── StartProcess ─────────────────────────────────────────────────────────────

function StartProcess() {
  ShowLoader("loader-process-wrap");
  ResetErrorMessages("error-message-process");
  document.getElementById("result-section").style.display = "none";

  var fileInput = document.getElementById("import-file");
  var fetchOptions;

  if (fileInput.files.length > 0) {
    var formData = new FormData();
    formData.append("file", fileInput.files[0]);
    fetchOptions = { method: "POST", body: formData };
  } else {
    fetchOptions = { method: "GET", signal: AbortSignal.timeout(30000) };
  }

  fetch("/run_process", fetchOptions)
    .then(function (response) {
      if (!response.ok)
        ShowErrorMessages("error-message-process", "HTTP " + response.status);
      return response.json();
    })
    .then(function (data) {
      HideLoader("loader-process-wrap");
      if (data.error) {
        ShowErrorMessages("error-message-process", data.error);
        return;
      }

      // Update comparison images with cache-bust
      document.getElementById("sourceFrame").src = bustCache(
        data.images.source,
      );
      document.getElementById("finalFrame").src = bustCache(data.images.final);
      document.getElementById("ocrFrame").src = bustCache(
        data.images.ocr_boxes,
      );

      // Render result metric cards
      renderResultCards(data.result);

      // Render pipeline thumbnails strip
      renderPipelineStrip(
        data.images.source,
        data.pipeline || [],
        data.images.final,
        data.images.ocr_boxes,
      );

      document.getElementById("result-section").style.display = "block";
      // Smooth scroll to results
      document
        .getElementById("result-section")
        .scrollIntoView({ behavior: "smooth" });
    })
    .catch(function (error) {
      HideLoader("loader-process-wrap");
      ShowErrorMessages("error-message-process", error.toString());
      console.error("StartProcess error:", error);
    });
}

// ─── Canvas / frame drawing ───────────────────────────────────────────────────

function CreateHomeAssistantMqttSensor() {
  fetch("/create_sensor")
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      document.getElementById("mqttStatus").innerHTML =
        data.mqtt && data.mqtt[1] && data.mqtt[1]["water"]
          ? "🟢 MQTT sensors created in Home Assistant"
          : "🔴 MQTT sensors creation error, check logs";
    })
    .catch(function () {
      document.getElementById("mqttStatus").innerHTML =
        "🔴 MQTT error, check logs";
    });
}

function EmptyCanvas(canvasid) {
  var canvas = document.getElementById(canvasid);
  if (canvas)
    canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
}

function LoadFrame() {
  EmptyCanvas("canvas");
  ShowLoader("loader-frame");

  var fileInput = document.getElementById("import-file");
  var canvas = document.getElementById("canvas");
  var ctx = canvas.getContext("2d");
  var img = new Image();

  function loadImage(data) {
    HideLoader("loader-frame");
    img.onload = function () {
      var angle =
        parseFloat(document.getElementById("input-rotate-image").value) || 0;
      drawImageWithRotation(ctx, img, angle, canvas);
      canvas.addEventListener("mousedown", startDrawing);
      canvas.addEventListener("mouseup", stopDrawing);
    };
    img.src = data;
  }

  if (fileInput.files.length > 0) {
    var reader = new FileReader();
    reader.onload = function (e) {
      loadImage(e.target.result);
    };
    reader.readAsDataURL(fileInput.files[0]);
  } else {
    fetch("/load_frame")
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        loadImage(d);
      })
      .catch(function (e) {
        console.error("Error loading frame:", e);
      });
  }

  document.getElementById("input-rotate-image").disabled = false;
  document.getElementById("select-rectangle").disabled = false;
  if (document.getElementById("button-send-edit")) {
    document.getElementById("button-send-edit").disabled = false;
  }

  document
    .getElementById("input-rotate-image")
    .addEventListener("input", function () {
      drawImageWithRotation(ctx, img, parseFloat(this.value) || 0, canvas);
    });

  function startDrawing(e) {
    var bounds = canvas.getBoundingClientRect();
    var sx = canvas.width / bounds.width;
    var sy = canvas.height / bounds.height;
    rectangles[currentRectangleIndex].coordinates = {
      x: (e.clientX - bounds.left) * sx,
      y: (e.clientY - bounds.top) * sy,
      width: 0,
      height: 0,
    };
    canvas.addEventListener("mousemove", drawRectangle);
  }

  function drawRectangle(e) {
    var rect = rectangles[currentRectangleIndex].coordinates;
    var bounds = canvas.getBoundingClientRect();
    rect.width =
      (e.clientX - bounds.left) * (canvas.width / bounds.width) - rect.x;
    rect.height =
      (e.clientY - bounds.top) * (canvas.height / bounds.height) - rect.y;
    drawImageWithRotation(
      ctx,
      img,
      parseFloat(document.getElementById("input-rotate-image").value) || 0,
      canvas,
    );
  }

  function stopDrawing() {
    canvas.removeEventListener("mousemove", drawRectangle);
    updateCoordinates();
  }
}

function selectRectangle() {
  currentRectangleIndex =
    parseInt(document.getElementById("select-rectangle").value) - 1;
  updateCoordinates();
}

function updateCoordinates() {
  EmptyTableBody("coordinates-table-body");
  var tbody = document.getElementById("coordinates-table-body");
  rectangles.forEach(function (rect) {
    var c = rect.coordinates;
    if (c.x === undefined) return;
    var row = tbody.insertRow();
    [rect.name, c.x, c.y, c.width, c.height].forEach(function (v) {
      row.insertCell().textContent = v;
    });
  });
}

function SendEdit() {
  var rotateValue =
    parseFloat(document.getElementById("input-rotate-image").value) || 0;
  rectangles.forEach(function (r) {
    r.rotate = rotateValue;
  });
  fetch("/send_edit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rectangles),
  })
    .then(function (r) {
      window.location.href = r.url;
    })
    .catch(function (e) {
      console.error("Error sending coordinates:", e);
    });
}

function SendConfig() {
  var form = document.getElementById("init-config-form");
  fetch("/save_config", { method: "POST", body: new FormData(form) })
    .then(function () {
      document
        .querySelector('div[data-target="#create-mqtt-sensor"] .step-trigger')
        .click();
    })
    .catch(function (e) {
      console.error("Error saving config:", e);
    });
}

// ─── Page init ────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", function () {
  if (
    window.location.pathname === "/" ||
    window.location.pathname === "/index"
  ) {
    var canvas = document.getElementById("canvas");
    var ctx = canvas.getContext("2d");
    var img = new Image();
    img.src = "static/img/frames/0.frame_origine.jpg";

    if (coordinates_from_flask) {
      rectangles.forEach(function (rect) {
        var c = coordinates_from_flask[rect.name];
        if (c)
          rect.coordinates = {
            x: c.x,
            y: c.y,
            width: c.width,
            height: c.height,
          };
      });
    }

    img.onload = function () {
      canvas.width = img.width;
      canvas.height = img.height;
      drawImageWithRotation(ctx, img, rotate_from_flask || 0, canvas);
    };
  }
});
