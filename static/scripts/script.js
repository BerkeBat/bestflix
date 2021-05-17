function reviewVotes(clickedVote) {
    const voteUp = document.getElementById('voteUp');
    const voteDown = document.getElementById('voteDown');
    const voteValue = document.getElementById('voteValue');
    if (document.getElementById(clickedVote) == voteUp){
        voteUp.disabled = true;
        voteUp.style.backgroundColor = 'green';
        voteDown.disabled = false;
        voteDown.style.backgroundColor = 'rgb(52, 58, 64)'
        voteValue.value = 'up';
    }else if(document.getElementById(clickedVote) == voteDown){
        voteUp.disabled = false;
        voteUp.style.backgroundColor = 'rgb(52, 58, 64)';
        voteDown.disabled = true;
        voteDown.style.backgroundColor = 'red';
        voteValue.value = 'down';
    }
}

function mustGiveVote(movieid) {
    const voteValue = document.getElementById('voteValue');
    const noVoteAlert = document.getElementById("noVoteAlert");
    const reviewForm = document.getElementById("reviewForm");
    if(voteValue.value == "none"){
            reviewForm.action = "javascript:void(0);";
            noVoteAlert.style.display = "block";
    } else{
            reviewForm.action = "/movie/" + movieid;
            noVoteAlert.style.display = "none";
    }
}


function giveRemoveOption(inorout) {
    const favouritedButton = document.getElementById('favouritedButton');
    if(inorout == "in"){
        favouritedButton.style.backgroundColor = "#dc3545";
        favouritedButton.style.borderColor = "#dc3545";
        favouritedButton.innerHTML = "<i class='fas fa-ban'></i> Remove";
    } else if (inorout == "out"){
        favouritedButton.style.backgroundColor = "#ba8e09";
        favouritedButton.style.borderColor = "#ba8e09";
        favouritedButton.innerHTML = "<i class='fas fa-check-circle'></i> Favourited";
    }
}




