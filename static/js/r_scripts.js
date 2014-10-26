/** @jsx React.DOM */
/**
 * Created by serdiuk on 25.10.2014.
 */

var board_size = 19;
var cell_size = 40;
var board = new Array(board_size * board_size);
var username = '';

Cell = React.createClass({
    getInitialState: function(){
        return {color: 0,
                game: this.props.game,
                status: ''}
    },
    onClick: function(e){
        console.log(this.state);
        if (this.state.game && this.state.status=='move' && this.state.color == 0) {
            msg = {
                command: 'move',
                cell: this.props.index
            };
            console.log(msg);
            ws_connection.send(JSON.stringify(msg));
        }
    },
    render: function() {
        var classes = 'cell';
        style = {
          width: cell_size,
          height: cell_size,
          display: 'table-cell'
        };
        color = this.state.color;
        inter_classes = '';
        if (color == 1)
            inter_classes = 'white';
        else
            if (color == 2)
                inter_classes = 'black';
        return <div className={classes} style={style}><div className={inter_classes} onClick={this.onClick}></div></div>
    }
});

for (i=0; i< board_size * board_size; i++)
    board[i] = new Cell({game: false, index: i});

Row = React.createClass({
   render: function () {
       var cells = [];
       for (i=0; i< board_size; i++){
           cell = board[this.props.index * board_size + i];
           cells.push(cell);
       }
       style = {
           display: 'table-row'
       };
       return <div style={style}>{cells}</div>
   }
});

BoardView = React.createClass({
    render: function() {
        var rows = [];
        for (i=0; i< board_size; i++){
            rows.push(new Row({index: i, game: this.props.game}))
        }
        el = document.getElementById('main');
        board_width = el.clientWidth - 10;
        board_width = board_width < 600 ? board_width : 600;
        cell_size = board_width / board_size;
        style = {
            'width': board_width,
            'height': board_width,
            display: 'table',
            'border-collapse': 'collapse'
        };
        return <div id="board" style={style}>{rows}</div>
    }
});

AlertView = React.createClass({
    getInitialState: function() {
        return {error: false,
                info: ''}
    },
    onClick: function(){
        this.setState({error: false});
    },
    render: function() {
        classes = this.state.error ? '' : 'hide';
        return <div id='error' className={classes} onClick={this.onClick}>{this.state.info}</div>
    }
});

AlertComponent = AlertView();

InfoView = React.createClass({
    render: function() {
        info = '';
        color = '';
        status = this.props.status;
        if (status == 'wait')
            info = 'Waiting for partner\'s move';
        if (status == 'created') {
            info = 'Waiting for partner';
        }
        if (status == 'move')
            info = 'Your move';
        if (status == 'win')
            info = 'You are won';
        if (status == 'loss')
            info = 'You are lost';
        if (status == 'draw')
            info = 'Draw';

        if (this.props.color == 1)
            color = <p>Your color is WHITE</p>;
        if (this.props.color == 2)
            color = <p>Your color is BLACK</p>;
        return <div id='info' class={classes}><p>{info}</p><p>{color}</p></div>
    }
});

ButtonsView = React.createClass({
    getInitialState: function() {
        return {type: 'create'}
    },
    onStart: function(){
        AlertComponent.setState({error:false});
        board.map(function(cell){
            if (cell.isMounted()) {
                cell.setState({color: 0})
            }
        });
        command = this.state.type == 'create' ? 'create' : 'join';
        color = this.refs.color1.getDOMNode().checked ? 1 : 2;
        msg = {
            command:  command,
            name: username };
        if (command == 'create'){
            msg.color = color;
        }
        ws_connection.send(JSON.stringify(msg));
    },
    onUserChange:function(e){
        username = e.target.value;
    },
    onTypeChange: function(e){
        value = e.target.value;
        this.setState({'type': value})
    },
    render: function() {
        classes = this.props.status != '' ? 'hide' : '' ;
        colorclasses = this.state.type == 'create' ? '': 'hide';
        return (
            <div className={classes}>
                <div>Your name: <input ref="username" type="text" onChange={this.onUserChange} /></div>
                <div>
                    <label for="type1">
                        <input id="type1" type="radio" ref="type1" name="type" value="create" defaultChecked={true} onClick={this.onTypeChange} />Create game
                    </label>
                    <label for="type2">
                        <input id="type1" type="radio" ref="type2" name="type" value="join" onClick={this.onTypeChange} />Join game
                    </label>
                </div>
                <div className={colorclasses}>
                    <input type="radio" ref="color1" name="color" value="1" defaultChecked={true} />White
                    <input type="radio" ref="color2" name="color" value="2" />Black
                </div>
                <button onClick={this.onStart}>Start</button>
            </div>
        )
    }
});

StatisticView = React.createClass({
    getInitialState: function() {
        return {table: []}
    },
    componentDidMount: function() {
        console.log('did mount');
        self = this;
        $.ajax({
            url: '/stats?username='+encodeURIComponent(username),
            method: 'get',
            dataType: 'json',
            success: function(data) {
                if (self.isMounted()) {
                    self.setState({table: data})
                }
            }
        })
    },
    render: function() {
        console.log('render statistic');
        table = this.state.table.map(function(row){
            return (<tr>
                <td>{row.position}</td>
                <td>{row.username}</td>
                <td>{row.wins}</td>
                <td>{row.losses}</td>
                <td>{row.draws}</td>
                </tr>)
        });
        return <table>
            <tr>
                <th>Pos.</th>
                <th>Name</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Draws</th>
            </tr>
            {table}
        </table>
    }
});

MainView = React.createClass({
    getInitialState: function() {
        return {view: 'board',
                game: false,
                status: '',
                color: 0};
    },
    componentDidUpdate: function(prevProps, prevState){
        game = this.state.game;
        status = this.state.status;
        board.map(function(cell){
            if (cell.isMounted()) {
                cell.setState({
                    game: game,
                    status: status
                });
            }
        })
    },
    onStatClick: function(){
        this.setState({view: 'stat'})
    },
    onReturnToBoard: function(){
        this.setState({view: 'board'})
    },
    render: function() {
        if (this.state.view == 'board') {
            return (
                <div>
                    <a href="javascript:void(0);" onClick={this.onStatClick}>Statistic</a>
                    <ButtonsView game={this.state.game} status={this.state.status} />
                    {AlertComponent}
                    <InfoView game={this.state.game} status={this.state.status} color={this.state.color} />
                    <BoardView game={this.state.game} />
                </div>
                )
        }else{
            return (
                <div>
                    <a href="javascript:void(0);" onClick={this.onReturnToBoard}>Return to board</a>
                    <StatisticView />
                </div>
                )
        }
    }
});

MainComponent = React.renderComponent(
    <MainView />,
    document.getElementById('main')
);