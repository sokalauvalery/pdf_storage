var socket,
    url = window.location;

function connect() {
    socket = new WebSocket('ws://' + url.host + '/socket');
    view_file_list();
    socket.onmessage = function (msg) {
        var data = JSON.parse(msg.data);

        switch (data.value){

            case "UPDATE_FILE_LIST":
                console.log('Got update file list request < ' + data.value + '>' );
                //TODO: This function uses from templates/index.html file. This is wrong!
                view_file_list();
                break;
            default:
                console.error('Got unexpected message < ' + data.value + '>')
        }
    };
}

window.onload = function () {
    connect();
};

window.onbeforeunload = function () {
    socket.close();
};


var view_pages = function (download_url) {
    $('.modal-body').load(download_url, function(){
        $('#modal-pages').modal({show:true});
    });
};
