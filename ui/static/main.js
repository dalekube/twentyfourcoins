
// main JavaScript file for the web platform

function requestSuccessful(){
  $("#loading").removeClass("loadingSpinner");
  $("#loading").addClass("loadingSuccess").html("Update Successful!");
  setTimeout(function(){
    $("#loading").fadeOut().empty().removeClass("loadingSuccess");
  }, 10000);
  
}

function getPriceHistory(){
    
    //Show the loading icon
    $("#loading").addClass("loadingSpinner").show();
    
    //Execute the function to update prices in the database
    $.ajax({
      url:"/price_history",
      type:"GET",
      contentType:"application/json",
      success: requestSuccessful
    });
    
}

function pricePrediction(coin){
    
    //Show the loading icon
    $("#loading").addClass("loadingSpinner").show();
    
    //Empty the price prediction box
    $("#pricePredictionBox").hide();
    
    //Execute the function to update prices in the database
    $.ajax({
      url: "/price_prediction",
      type: "POST",
      data: JSON.stringify({COIN: coin.value}),
      dataType: "json",
      contentType:"application/json",
      success: function(data){
        parsed_data = JSON.parse(data);
        
        // Display the price prediction details
        $("#predict_coin").html(coin.value);
        $("#predict_time").html("Latest Candle Time = " + JSON.parse(JSON.stringify(parsed_data.predict_time)));
        $("#predict_now").html("Current Time = " + JSON.parse(JSON.stringify(parsed_data.predict_now)));
        $("#predict_close").html("Latest Close Price = " + JSON.parse(JSON.stringify(parsed_data.predict_close)));
        $("#predict_prediction").html("Price Prediction = " + JSON.parse(JSON.stringify(parsed_data.prediction)));
        $("#predict_change").html("Expected Price Change = " + JSON.parse(JSON.stringify(parsed_data.expected_change)));
        
        $("#pricePredictionBox").show();
        requestSuccessful();
        
      }
    });
    
}