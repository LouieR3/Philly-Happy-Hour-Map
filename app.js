const http = require('http')
const port = 3000
console.log("Hello")

const server = http.createServer(function(req, res) {
    res.writeHead(200, {"Content-Type" : "text/html"})
    res.write("Hello Node")
    res.end()
})
server.listen(port, function(error){
    if (error) {
        console.log("Something went wrong", error)
    } else {
        console.log("Server listing to port " + port)
    }
})