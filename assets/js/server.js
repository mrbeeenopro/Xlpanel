$(document).ready(()=>{
    $(".form form").on( "submit", function( event ) {
        const egg = $("select[name=\"egg\"]").val();
        if (!egg || egg === "_") {
            alert("Please fill out the form.")
            event.preventDefault();
        }
    });
})

function del() {
    if(confirm("Do you REALLY want to delete this server?")) {
        $(".loading").fadeIn()
        fetch("", {
            method: "delete"
        })
        .then(r => r.json())
        .then(r => {
            if (r.status == "ok") {
                alert("Deleted.")
                window.location.href = "/servers"
            } else {
                alert(r.message)
                console.log(r.message)
                $(".loading").fadeOut()
            }
        })
    }
}
