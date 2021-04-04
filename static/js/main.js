
// main JavaScript file for the web platform

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
        
        // Parse the incoming data
        stats = data.stats;
        charts = data.charts;
        
        // Parse the prediction timestamps and present in locale
        var actual_time = JSON.parse(JSON.stringify(stats.actual_time));
        actual_time = actual_time.split(" ");
        var actual_time_dt = actual_time[0].split("-");
        const predict_year = parseInt(actual_time_dt[0]);
        const predict_month = parseInt(actual_time_dt[1])-1;
        const predict_day = parseInt(actual_time_dt[2]);
        actual_time = actual_time[1].split(":");
        const predict_hours = parseInt(actual_time[0]);
        const predict_min = parseInt(actual_time[1]);
        const predict_sec = parseInt(actual_time[2]);
        actual_time = new Date(Date.UTC(predict_year,predict_month,predict_day,predict_hours,predict_min,predict_sec)).toLocaleString();
        
        // Display the price prediction details
        $("#predict_coin").html(coin_name + " (" + coin_code + ")");
        $("#actual_time").html(actual_time);
        $("#actual_close").html(JSON.parse(JSON.stringify(stats.actual_close)));
        
        const change_direction = JSON.parse(JSON.stringify(stats.change_direction));
        var indicator = "<i class='fas fa-caret-down'></i>";
        if (change_direction == 'up') {
          indicator = "<i class='fas fa-caret-up'></i>";
        }
        $("#predict_prediction").html(indicator + JSON.parse(JSON.stringify(stats.prediction)));
        $("#predict_change").html(indicator + JSON.parse(JSON.stringify(stats.expected_change)));
        $("#predict_change_pct").html(" (" + JSON.parse(JSON.stringify(stats.expected_change_pct)) + ")");
        
        // Parse the training timestamp and present in locale
        var training_time = JSON.parse(JSON.stringify(stats.stats_training_time));
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
        $("#stats_mae").html(JSON.parse(JSON.stringify(stats.stats_mae)));
        $("#stats_mape").html(JSON.parse(JSON.stringify(stats.stats_mape)));
        
        $("#mainChart").html(Bokeh.embed.embed_item(charts));
        $("#pricePredictionBox").show();
            
          } // end of success
          
        }); // end of AJAX call
    
}

// Load an initial coin
$(window).on('load', function(){
  pricePrediction({value:"Basic Attention Token:BAT-USDC"}, 'N');
});


