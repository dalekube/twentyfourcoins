
// main JavaScript file for the web platform

$(document).on("click","#modelDetailsButton",function(){
  $("#modelDetailsCaret").toggleClass("rotate");
});

function pricePrediction(coin, userclick){
    
    var coin_split = coin.value.split(":");
    const coin_name = coin_split[0];
    const coin_code = coin_split[1];
    
    //Execute the function to update prices in the database
    $.ajax({
      url: "/price_prediction",
      type: "POST",
      data: JSON.stringify({COIN: coin_code, CLICK:userclick}),
      contentType:"application/json",
      error: function(){
        msg = "Failed to retrieve the forecast data for " + coin_name + " (" + coin_code + ")";
        window.location.replace("/error?msg=" + msg);
      },
      success: function(data){
        parsed_data = JSON.parse(data);
        
        // Parse the prediction timestamps and present in locale
        var predict_time = JSON.parse(JSON.stringify(parsed_data.predict_time));
        predict_time = predict_time.split(" ");
        var predict_time_dt = predict_time[0].split("-");
        const predict_year = parseInt(predict_time_dt[0]);
        const predict_month = parseInt(predict_time_dt[1])-1;
        const predict_day = parseInt(predict_time_dt[2]);
        predict_time = predict_time[1].split(":");
        const predict_hours = parseInt(predict_time[0]);
        const predict_min = parseInt(predict_time[1]);
        const predict_sec = parseInt(predict_time[2]);
        predict_time = new Date(Date.UTC(predict_year,predict_month,predict_day,predict_hours,predict_min,predict_sec)).toLocaleString();
        
        // Display the price prediction details
        $("#predict_coin").html(coin_name + " (" + coin_code + ")");
        $("#predict_time").html(predict_time);
        $("#predict_close").html(JSON.parse(JSON.stringify(parsed_data.predict_close)));
        
        const change_direction = JSON.parse(JSON.stringify(parsed_data.change_direction));
        var indicator = "<i class='fas fa-caret-down'></i>";
        if (change_direction == 'up') {
          indicator = "<i class='fas fa-caret-up'></i>";
        }
        $("#predict_prediction").html(indicator + JSON.parse(JSON.stringify(parsed_data.prediction)));
        $("#predict_change").html(indicator + JSON.parse(JSON.stringify(parsed_data.expected_change)));
        $("#predict_change_pct").html(" (" + JSON.parse(JSON.stringify(parsed_data.expected_change_pct)) + ")");
        
        // Parse the training timestamp and present in locale
        var training_time = JSON.parse(JSON.stringify(parsed_data.stats_training_time));
        training_time = training_time.split(" ");
        var training_date = training_time[0].split("-");
        const year = parseInt(training_date[0]);
        const month = parseInt(training_date[1])-1;
        const day = parseInt(training_date[2]);
        training_time = training_time[1].split(":");
        const hours = parseInt(training_time[0]);
        const min = parseInt(training_time[1]);
        const sec = parseInt(training_time[2]);
        training_date = new Date(Date.UTC(year,month,day,hours,min,sec)).toLocaleString();
        
        $("#stats_training_time").html(training_date);
        $("#stats_mae").html(JSON.parse(JSON.stringify(parsed_data.stats_mae)));
        $("#stats_mape").html(JSON.parse(JSON.stringify(parsed_data.stats_mape)));
        
      }
    });
    
}

// Load an initial free coin
$(window).on('load', function(){
  pricePrediction({value:"Basic Attention Token:BAT-USDC"}, 'N');
});


