/**
 * Created by serdiuk on 24.10.2014.
 */

var ws_connection = null;

function connect() {
    url = protocol + '://' + location.hostname+(location.port ? ':'+location.port: '') + '/game';
    ws_connection = new WebSocket(url);
    ws_connection.onclose = onclose;
    ws_connection.onmessage = onmessage;
    ws_connection.onopen = onopen;
}

function onmessage(event) {
    data = JSON.parse(event.data);
    if ('event' in data){
        if (data.event == 'error'){
            show_error(data.info);
        }
        if (data.event == 'created'){
            MainComponent.setState({status: 'created', color: data.color});
            return;
        }
        if (data.event == 'start_game'){
            MainComponent.setState({status: data.info, game: true, color: data.color});
            return;
        }
        if (data.event == 'end_game'){
            MainComponent.setState({status: data.info, game: false});
            return
        }
        if (data.event == 'move'){
            board[data.cell].setState({color:data.color});
            MainComponent.setState({status: data.status});
            return;
        }
    }
}

function onclose(event){

    show_error(event.reason || 'Connection reset. Trying to reconnect');
    if (MainComponent.isMounted())
        MainComponent.setState({game: true, status: ''});
    ws_connection = null;
    setTimeout(connect, 10000);
}

function onopen(){
    setTimeout(ping, 50000);
    if (AlertComponent.isMounted())
        AlertComponent.setState({error: false});
    if (MainComponent.isMounted())
        MainComponent.setState({game: false, status: ''});
}

function ping(){
  if (ws_connection){
      msg = {
          command: 'ping'
      };
      ws_connection.send(JSON.stringify(msg));
      setTimeout(ping, 50000);
  }
}

function show_error(text){
    console.log(text);
    AlertComponent.setState({error: true, info: text});
}
connect();