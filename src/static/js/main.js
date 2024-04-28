function createTableFromObject(obj) {
    var table = document.createElement('table');

    // Add header row
    var headerRow = table.insertRow();
    for (var key in obj) {
        var th = document.createElement('th');
        th.textContent = key;
        headerRow.appendChild(th);
    }

    // Add data rows
    var dataRow = table.insertRow();
    for (var key in obj) {
        var td = document.createElement('td');
        td.textContent = obj[key];
        dataRow.appendChild(td);
    }

    return table;
}

function startProcess() {
    fetch('/run_process')
        .then(response => response.json())
        .then(data => {
            document.getElementById('sourceFrame').src = data.image.image_source;
            document.getElementById('improveFrame').src = data.image.image_improve;
            document.getElementById('azureVision').src = data.image.image_vision;
            console.log(data.result);
            var tableContainer = document.getElementById('tableResult');
            tableContainer.appendChild(createTableFromObject(data.result));
        });

        
}

function toggleVideoFeed() {
    var video = document.getElementById('videoFeed');
    if (video.style.display === 'none') {
        video.style.display = 'block';
    } else {
        video.style.display = 'none';
    }
}

CreateHomeAssistantMqttSensor

function CreateHomeAssistantMqttSensor() {
    fetch('/create_sensor')
        .then(response => response.json())
        .then(data => {
            console.log(data.mqtt[0]["water"]);
            if (data.mqtt[0]["water"]) {
                document.getElementById('mqttStatus').innerHTML = "MQTT sensors created in home assistant";
            } else {
                document.getElementById('mqttStatus').innerHTML = "MQTT sensors creation error, check the logs";
            }
            
        });

        
}