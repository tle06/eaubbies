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

function ShowErrorMessages(errorMessages) {
  document.getElementById(errorid).style.display = "block";
  document.getElementById(errorid).textContent = errorMessages;
}

function ResetErrorMessages(errorid) {
  document.getElementById(errorid).style.display = "none";
  document.getElementById(errorid).textContent = "";
}

function EmptyTableBody(bodyid) {
  tbody = document.getElementById(bodyid);
  rows = tbody.querySelectorAll("tr");
  rows.forEach((row) => row.remove());
}
function StartProcess() {
  ShowLoader("loader-process", "inline");
  ResetErrorMessages("error-message-process");
  EmptyTableBody("process-table-result-body");

  fetch("/run_process")
    .then((response) => response.json())
    .then((data) => {
      if (data.hasOwnProperty("error")) {
        HideLoader("loader-process");
        console.log("Error:", data.error);
        ShowErrorMessages("error-message-process");
      } else {
        HideLoader("loader-process");
        console.log(data);
        document.getElementById("sourceFrame").src = data.images.image_source;
        document.getElementById("improveFrame").src = data.images.image_improve;
        document.getElementById("azureVision").src = data.images.image_vision;
        console.log(data.result);
        var table = document.getElementById("process-table-result");
        table.appendChild(updateTableFromObject(table, data.result));
      }
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

  fetch("/load_frame")
    .then((response) => response.json())
    .then((data) => {
      HideLoader("loader-frame");
      console.log(rectangles);

      var img = new Image();
      var canvas = document.getElementById("canvas");
      var ctx = canvas.getContext("2d");

      img.onload = function () {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0, img.width, img.height);

        // Listen for mouse events
        canvas.addEventListener("mousedown", startDrawing);
        canvas.addEventListener("mouseup", stopDrawing);
      };

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
        drawRectangles();
      }

      function drawRectangles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, img.width, img.height);
        rectangles.forEach(function (rect, index) {
          console.log(index);
          var coordinates = rect.coordinates;
          ctx.strokeStyle = rect.color;
          ctx.lineWidth = 2; // Set stroke width
          ctx.strokeRect(
            coordinates.x + 0.5,
            coordinates.y + 0.5,
            coordinates.width,
            coordinates.height,
          ); // Draw rectangle's edge
        });
      }

      function stopDrawing() {
        // Stop drawing and remove mousemove event listener
        canvas.removeEventListener("mousemove", drawRectangle);
        updateCoordinates(); // Update coordinates on mouse up
      }

      img.src = data;
    });
}

function selectRectangle() {
  currentRectangleIndex =
    parseInt(document.getElementById("rectangleSelector").value) - 1;
  updateCoordinates();
}

function updateCoordinates() {
  // Display coordinates in a div
  var coordinatesDiv = document.getElementById("coordinates");
  coordinatesDiv.innerHTML = "";

  rectangles.forEach(function (rect, index) {
    var coordinates = rect.coordinates;
    var name = rect.name;
    if (
      coordinates.x !== undefined &&
      coordinates.y !== undefined &&
      coordinates.width !== undefined &&
      coordinates.height !== undefined
    ) {
      // Display coordinates only if they are defined
      coordinatesDiv.innerHTML +=
        name +
        ": Position (" +
        coordinates.x +
        ", " +
        coordinates.y +
        "), Size (" +
        coordinates.width +
        ", " +
        coordinates.height +
        ")" +
        "<br>";
    }
  });
}

function SendCoordinates() {
  // Send the coordinates stored in the global variable 'rectangles' to the Flask backend
  fetch("/send_coordinates", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(rectangles),
  })
    .then((response) => response.json())
    .then((data) => {
      console.log("Coordinates sent successfully:", data);
    })
    .catch((error) => {
      console.error("Error sending coordinates:", error);
    });
}
