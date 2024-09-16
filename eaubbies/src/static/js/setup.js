var rectangles = [
  { name: "all", coordinates: {}, color: "blue" },
  { name: "integer", coordinates: {}, color: "red" },
  { name: "digit", coordinates: {}, color: "green" },
];

var currentRectangleIndex = 0;

function ShowLoader(loaderid, display = "block") {
  document.getElementById(loaderid).style.display = display;
}

function HideLoader(loaderid) {
  document.getElementById(loaderid).style.display = "none";
}

function updateTableFromObject(table, obj) {
  // Add data rows
  for (var key in obj) {
    var dataRow = table.insertRow();
    var propertyNameCell = dataRow.insertCell();
    propertyNameCell.textContent = key;
    var propertyValueCell = dataRow.insertCell();
    propertyValueCell.textContent = obj[key];
  }
}

function ShowErrorMessages(errorid, errorMessages) {
  document.getElementById(errorid).style.display = "block";
  var errorElement = document.getElementById(errorid);
  var existingParagraph = errorElement.querySelector("p");
  existingParagraph.textContent = errorMessages;
  document.getElementById(errorid).appendChild(existingParagraph);
}

function ResetErrorMessages(errorid) {
  document.getElementById(errorid).style.display = "none";
  var errorElement = document.getElementById(errorid);
  var existingParagraph = errorElement.querySelector("p");
  if (existingParagraph) {
    existingParagraph.textContent = "";
  }
}

function EmptyTableBody(bodyid) {
  tbody = document.getElementById(bodyid);
  rows = tbody.querySelectorAll("tr");
  rows.forEach((row) => row.remove());
}

// Function to draw the image with rotation
function drawImageWithRotation(ctx, img, angle, canvas) {
  ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear the canvas

  // Move the canvas origin to the center
  ctx.translate(canvas.width / 2, canvas.height / 2);

  // Rotate the canvas
  ctx.rotate((angle * Math.PI) / 180);

  // Draw the rotated image, centered
  ctx.drawImage(
    img,
    -img.width / 2,
    -img.height / 2,
    canvas.width,
    canvas.height,
  );

  // Reset the canvas transformation
  ctx.setTransform(1, 0, 0, 1, 0, 0);

  rectangles.forEach(function (rect) {
    var coordinates = rect.coordinates;
    ctx.strokeStyle = rect.color;
    ctx.lineWidth = 2;
    ctx.strokeRect(
      coordinates.x,
      coordinates.y,
      coordinates.width,
      coordinates.height,
    );
  });
}

// functions triggered by UI
function StartProcess() {
  ShowLoader("loader-process", "inline");
  ResetErrorMessages("error-message-process");
  EmptyTableBody("process-table-result-body");

  var fileInput = document.getElementById("import-file");
  var formData = new FormData();

  var requestUrl = "/run_process";
  var requestMethod = "GET";
  var fetchOptions = {
    method: requestMethod,
    signal: AbortSignal.timeout(30000),
  };

  if (fileInput.files.length > 0) {
    // Send file via POST request
    requestMethod = "POST";
    formData.append("file", fileInput.files[0]);
    fetchOptions = {
      method: requestMethod,
      body: formData,
    };
  }

  fetch(requestUrl, fetchOptions)
    .then((response) => {
      console.log("Response:", response);
      if (!response.ok) {
        ShowErrorMessages("error-message-process", response);
      }
      return response.json();
    })
    .then((data) => {
      HideLoader("loader-process");
      if (data.hasOwnProperty("error")) {
        console.log("Error:", data.error);
        ShowErrorMessages("error-message-process", data.error);
      } else {
        console.log(data);
        document.getElementById("sourceFrame").src = data.images.image_source;
        document.getElementById("improveFrame").src = data.images.image_improve;
        document.getElementById("azureVision").src = data.images.image_vision;
        console.log(data.result);
        var table = document.getElementById("process-table-result");
        updateTableFromObject(table, data.result);
      }
    })
    .catch((error) => {
      console.error("Error sending file:", error);
    });
}

function CreateHomeAssistantMqttSensor() {
  fetch("/create_sensor")
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      if (data.mqtt[1]["water"]) {
        document.getElementById("mqttStatus").innerHTML =
          "🟢 MQTT sensors created in home assistant";
      } else {
        document.getElementById("mqttStatus").innerHTML =
          "🔴MQTT sensors creation error, check the logs";
      }
    })
    .catch((error) => {
      console.error("Error creating mqtt sensor:", error);
      document.getElementById("mqttStatus").innerHTML =
        "🔴MQTT sensors creation error, check the logs";
    });
}

function EmptyCanvas(canvasid) {
  var canvas = document.getElementById(canvasid);
  if (canvas) {
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

function LoadFrame() {
  EmptyCanvas("canvas");
  ShowLoader("loader-frame");

  var fileInput = document.getElementById("import-file");
  var img = new Image();
  var ctx = canvas.getContext("2d");
  var data;

  if (fileInput.files.length > 0) {
    // File upload
    var file = fileInput.files[0];
    var reader = new FileReader();
    reader.onload = function (e) {
      data = e.target.result;
      loadImage(data);
    };
    reader.readAsDataURL(file);
  } else {
    // API call
    fetch("/load_frame")
      .then((response) => response.json())
      .then((data) => {
        data = data;
        loadImage(data);
      })
      .catch((error) => {
        console.error("Error loading image from API:", error);
      });
  }

  document.getElementById("input-rotate-image").disabled = false;
  document.getElementById("select-rectangle").disabled = false;
  if (document.getElementById("button-send-edit")) {
    document.getElementById("button-send-edit").disabled = false;
  }

  function loadImage(data) {
    HideLoader("loader-frame");
    var canvas = document.getElementById("canvas");

    img.onload = function () {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0, img.width, img.height);

      // Listen for mouse events
      canvas.addEventListener("mousedown", startDrawing);
      canvas.addEventListener("mouseup", stopDrawing);
    };

    img.src = data;
  }

  function startDrawing(e) {
    // Update coordinates when drawing starts
    var rectBounds = canvas.getBoundingClientRect();
    var scaleX = canvas.width / rectBounds.width;
    var scaleY = canvas.height / rectBounds.height;
    var rect = {
      x: (e.clientX - rectBounds.left) * scaleX,
      y: (e.clientY - rectBounds.top) * scaleY,
      width: 0,
      height: 0,
    };
    rectangles[currentRectangleIndex].coordinates = rect;
    canvas.addEventListener("mousemove", drawRectangle);
  }

  function drawRectangle(e) {
    // Update coordinates while drawing
    //if (rectangles.length === 0) return;
    var rect = rectangles[currentRectangleIndex].coordinates;
    var rectBounds = canvas.getBoundingClientRect();
    var scaleX = canvas.width / rectBounds.width;
    var scaleY = canvas.height / rectBounds.height;

    rect.width = (e.clientX - rectBounds.left) * scaleX - rect.x;
    rect.height = (e.clientY - rectBounds.top) * scaleY - rect.y;
    var angle =
      parseFloat(document.getElementById("input-rotate-image").value) || 0;
    drawImageWithRotation(
      (ctx = ctx),
      (img = img),
      (angle = angle),
      (canvas = canvas),
    );
  }

  function stopDrawing() {
    // Stop drawing and remove mousemove event listener
    canvas.removeEventListener("mousemove", drawRectangle);
    updateCoordinates(); // Update coordinates on mouse up
  }

  document
    .getElementById("input-rotate-image")
    .addEventListener("input", function () {
      var angle = parseFloat(this.value) || 0;
      drawImageWithRotation(
        (ctx = ctx),
        (img = img),
        (angle = angle),
        (canvas = canvas),
      );
    });

  //img.src = data;
}

function selectRectangle() {
  currentRectangleIndex =
    parseInt(document.getElementById("select-rectangle").value) - 1;
  updateCoordinates();
}

function updateCoordinates() {
  var table = document.getElementById("coordinates-table-body");
  EmptyTableBody("coordinates-table-body");

  rectangles.forEach(function (rect, index) {
    var coordinates = rect.coordinates;
    var name = rect.name;
    if (
      coordinates.x !== undefined &&
      coordinates.y !== undefined &&
      coordinates.width !== undefined &&
      coordinates.height !== undefined
    ) {
      // Create a new row
      var row = table.insertRow();
      var nameCell = row.insertCell();
      nameCell.textContent = name;
      var xCell = row.insertCell();
      xCell.textContent = coordinates.x;
      var yCell = row.insertCell();
      yCell.textContent = coordinates.y;
      var widthCell = row.insertCell();
      widthCell.textContent = coordinates.width;
      var heightCell = row.insertCell();
      heightCell.textContent = coordinates.height;
    }
  });
}

function SendEdit() {
  // Send the coordinates stored in the global variable 'rectangles' to the Flask backend
  var rotateValue =
    parseFloat(document.getElementById("input-rotate-image").value) || 0;
  rectangles.forEach(function (rect) {
    rect.rotate = rotateValue;
  });
  console.log(rectangles);

  fetch("/send_edit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(rectangles),
  })
    .then((response) => {
      console.log("Coordinates sent successfully:", response);
      window.location.href = response.url;
    })
    .then((data) => {
      console.log("Coordinates sent successfully:", data);
    })
    .catch((error) => {
      console.error("Error sending coordinates:", error);
    });
}

function SendConfig() {
  var form = document.getElementById("init-config-form");
  var formData = new FormData(form);

  fetch("/save_config", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      document
        .querySelector('div[data-target="#create-mqtt-sensor"] .step-trigger')
        .click();
    })
    .catch((error) => {
      console.error("Error saving config:", error);
    });
}

document.addEventListener("DOMContentLoaded", function () {
  // Check if the current URL path is '/index'
  if (
    window.location.pathname === "/index" ||
    window.location.pathname === "/"
  ) {
    // Get the canvas element and its context
    var canvas = document.getElementById("canvas");
    var ctx = canvas.getContext("2d");

    // Create a new image
    var img = new Image();
    img.src = "static/img/frames/origine.jpg"; // Replace with your image path

    // Transforming the object into the desired format
    if (coordinates_from_flask) {
      rectangles.forEach((rect) => {
        if (coordinates_from_flask[rect.name]) {
          rect.coordinates = {
            x: coordinates_from_flask[rect.name].x,
            y: coordinates_from_flask[rect.name].y,
            width: coordinates_from_flask[rect.name].width,
            height: coordinates_from_flask[rect.name].height,
          };
        }
      });
    }
    // Draw the image onto the canvas once it has loaded
    img.onload = function () {
      console.log(rotate_from_flask);
      canvas.width = img.width;
      canvas.height = img.height;
      drawImageWithRotation(
        (ctx = ctx),
        (img = img),
        (angle = rotate_from_flask),
        (canvas = canvas),
      );
    };
  }
});
