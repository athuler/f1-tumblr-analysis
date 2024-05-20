<?php

########################
#### Connect to DB  ####
########################
$conn = new PDO('sqlite:postDb.db');


########################
#### Read Race Data ####
########################
	
$file = "race_data.json";
$raceData = json_decode(file_get_contents($file), true);
$season = 2023;

function filterBySeason($var) {
	global $season;
	return $var["year"]==$season;
}

function sortByRound($a,$b) {
	if($a < $b) {
		return -1;
	} else if ($a > $b) {
		return 1;
	} else {
		return 0;
	}
	
}

// Filter For Current Season
$raceData = array_filter($raceData, "filterBySeason");

// Sort By Round #
uasort($raceData, "sortByRound");



########################
#### Get Post Data  ####
########################

$numPostsArray = array();
$postsOverTime = array();

foreach ($raceData as $currentRace => $currentRaceData) {
	// Get Number of Posts
	
	$tbl = $currentRaceData["table_name"];
	$sql = $conn->prepare("SELECT COUNT(*) AS `numPosts` FROM `$tbl`");
	$sql->execute([]);
	$countData = $sql->fetchAll();
	
	$numPosts = $countData[0]["numPosts"];
	
	$raceData[$currentRace]["num_posts"] = $numPosts;
	
	$numPostsArray[$currentRaceData["name"]] = $numPosts;
	
	// Get Posts Over Duration Of Race
	$sql = $conn->prepare("
		SELECT
			strftime('%Y-%m-%d %H:%M', datetime(timestamp, 'unixepoch')) AS minute_start,
			COUNT(*) AS post_count,
			AVG(postLength) AS avgPostLength,
			AVG(emotionScore) AS avgEmotionScore,
			AVG(ABS(emotionScore)) AS absAvgEmotionScore
		FROM \"$tbl\"
		GROUP BY 
			minute_start;
		");
	$sql->execute([]);
	$posts = $sql->fetchAll();
	
	foreach($posts as $thisTime) {
		$postsOverTime[$currentRace]["datetime"][] = $thisTime["minute_start"];
		$postsOverTime[$currentRace]["numPosts"][] = $thisTime["post_count"];
		$postsOverTime[$currentRace]["avgPostLength"][] = (int)$thisTime["avgPostLength"];
		$postsOverTime[$currentRace]["avgEmotionScore"][] = $thisTime["avgEmotionScore"];
		$postsOverTime[$currentRace]["absAvgEmotionScore"][] = $thisTime["absAvgEmotionScore"];
	}
	
	$postsOverTime[$currentRace]["gpStart"] = $currentRaceData["timestamps"]["gp_start"];
	$postsOverTime[$currentRace]["gpEnd"] = $currentRaceData["timestamps"]["gp_end"];
	
}


?>
<!DOCTYPE html>
<html lang="en">
	<head>
		<!-- meta -->
		<meta charset="utf-8">
		<meta name="viewport" content="width=device-width, initial-scale=1">
		
		<!-- Title -->
		<title>F1 Tumblr Analysis</title>
		
		<!-- Bootstrap Stylesheet -->
		<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
		
		<!-- Plotly -->
		<script src="https://cdn.plot.ly/plotly-2.31.1.min.js" charset="utf-8"></script>

	</head>
	<body class="container-fluid bg-light" >
		
		<h1>F1 Tumblr Analysis</h1><br/>
		
		<h2>Number of Posts by Race</h2>
		<div id="numPostsChart" style="height:600px;"></div>
		<p><?=number_format(array_sum($numPostsArray));?> total posts</p>
		<script>
			
			var numPostsData = [{
				name: 'Number of Posts',
				x: ['<?=implode("','",array_keys($numPostsArray));?>'],
				y: ['<?=implode("','",array_values($numPostsArray));?>'],
				marker: {
					color: 'rgb(171, 171, 171)'
				},
				type: 'bar'
			}];
			
			var numPostsLayout = {
				title: 'Number of Posts By Race',
				showlegend: false,
				paper_bgcolor: 'rgba(0,0,0,0)',
				plot_bgcolor: 'rgba(0,0,0,0)',
				legend: {
					x: 0,
					xanchor: 'left',
					y: 1,
					traceorder: 'normal',
					font: {
						family: 'sans-serif',
						size: 12,
						color: '#000'
					},
					bgcolor: '#E2E2E2',
					bordercolor: 'rgba(0,0,0,0)',
					borderwidth: 2
				},
				xaxis: {
					autorange: true,
				},
				yaxis: {
					title: "# of Posts",
					autorange: true,
					type: 'linear'
				}
			};

			var numPostsParameters = {
				responsive: true,
				displayModeBar: true
			};
			
			Plotly.newPlot('numPostsChart', numPostsData, numPostsLayout, numPostsParameters);
		</script>
		<br/>
		
		
		<h2>Posts During Each Race</h2>
		<?php foreach($raceData as $currentRace => $currentRaceData) {
			$raceId = str_replace(" ","",$currentRaceData["name"]);
			?>
			
		<h3>Race <?=$currentRaceData["round"];?>: <?=$currentRaceData["name"];?></h3>
		<div id="<?=$raceId;?>Chart" style="height:600px;"></div>
		<script>
			
			var <?=$raceId;?>Data = [{
				name: 'Posts',
				x: ['<?=implode("','",$postsOverTime[$currentRace]["datetime"]);?>'],
				y: ['<?=implode("','",$postsOverTime[$currentRace]["numPosts"]);?>'],
				yaxis: 'y1',
				marker: {
					color: 'rgb(171, 171, 171)'
				},
				type: 'bar'
			},{
				name: 'Avg Post Length',
				x: ['<?=implode("','",$postsOverTime[$currentRace]["datetime"]);?>'],
				y: ['<?=implode("','",$postsOverTime[$currentRace]["avgPostLength"]);?>'],
				yaxis: 'y2',
				marker: {
					color: 'rgb(141, 224, 125)'
				},
				opacity:0.5,
				type: 'line'
			},{
				name: 'Avg Abs Emotion',
				x: ['<?=implode("','",$postsOverTime[$currentRace]["datetime"]);?>'],
				y: ['<?=implode("','",$postsOverTime[$currentRace]["absAvgEmotionScore"]);?>'],
				yaxis: 'y3',
				marker: {
					color: 'rgb(103, 34, 251)'
				},
				opacity:0.5,
				type: 'line'
			},{
				name: 'Avg Emotion',
				x: ['<?=implode("','",$postsOverTime[$currentRace]["datetime"]);?>'],
				y: ['<?=implode("','",$postsOverTime[$currentRace]["avgEmotionScore"]);?>'],
				yaxis: 'y3',
				marker: {
					color: 'rgb(104, 2, 41)'
				},
				opacity:0.5,
				type: 'line'
			},];
			
			var <?=$raceId;?>Layout = {
				title: 'Posts During The <?=$currentRaceData["name"];?> GP <?=$currentRaceData["year"];?>',
				showlegend: true,
				paper_bgcolor: 'rgba(0,0,0,0)',
				plot_bgcolor: 'rgba(0,0,0,0)',
				legend: {
					x: 0,
					xanchor: 'left',
					y: 1,
					traceorder: 'normal',
					font: {
						family: 'sans-serif',
						size: 12,
						color: '#000'
					},
					bgcolor: '#E2E2E2',
					bordercolor: 'rgba(0,0,0,0)',
					borderwidth: 2
				},
				xaxis: {
					type: "date",
					domain: [0, 0.8],
					autorange: false,
					range: ['<?=date(
						"Y-m-d H:m",
						$currentRaceData["timestamps"]["gp_start"]-60*60*2
						);?>', '<?=date("Y-m-d H:m", $currentRaceData["timestamps"]["gp_end"] + 60*60*2);?>'],
					rangeslider: {
						range: ['<?=date(
						"Y-m-d H:m",
						$currentRaceData["timestamps"]["gp_start"]-60*60*2
						);?>', '<?=date("Y-m-d H:m", $currentRaceData["timestamps"]["gp_end"]+60*60*2);?>']
					}
				},
				yaxis: {
					title: "# of Posts",
					autorange: true,
					type: 'linear',
					fixedrange: false,
					minallowed: 0,
				},
				yaxis2: {
					title: "Post Length",
					autorange: false,
					range: [0, 200],
					fixedrange: false,
					type: 'linear',
					overlaying: 'y',
					side: 'right',
					minallowed: 0,
					position: 0.9
				},
				yaxis3: {
					title: "Emotion Score",
					autorange: false,
					range: [-1,1],
					fixedrange: false,
					type: 'linear',
					overlaying: 'y',
					side: 'right',
				},
				shapes: [
					<?php foreach($currentRaceData["timestamps"] as $sessionName => $timestamp) {
						$session = explode("_", $sessionName)[0];
						$startEnd = explode("_", $sessionName)[1];
						
						if($startEnd == "end") {
							continue;
						}
						
					?>
					
					// Highlight Race
					{
						type: 'rect',
						xref: 'x',
						// y-reference is assigned to the plot paper [0,1]
						yref: 'paper',
						x0: '<?=date("Y-m-d H:m", $currentRaceData["timestamps"][$session . "_start"]);?>',
						y0: 0,
						x1: '<?=date("Y-m-d H:m", $currentRaceData["timestamps"][$session . "_end"]);?>',
						y1: 1,
						fillcolor: 'rgb(200, 0, 0)',
						opacity: 0.05,
						line: {
							width: 0
						}
					},
					<?php } ?>
				],
			};

			var <?=$raceId;?>Parameters = {
				responsive: true,
				displayModeBar: true
			};
			
			Plotly.newPlot('<?=$raceId;?>Chart', <?=$raceId;?>Data, <?=$raceId;?>Layout, <?=$raceId;?>Parameters);
		</script>
		<br/>
			
		<?php } ?>
		
		
		
		
		<!-- Bootstrap Scripts -->
		<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
		<script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.11.8/dist/umd/popper.min.js" integrity="sha384-I7E8VVD/ismYTF4hNIPjVp/Zjvgyol6VFvRkX/vR+Vc4jQkC+hVqc2pM8ODewa9r" crossorigin="anonymous"></script>
		<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.min.js" integrity="sha384-0pUGZvbkm6XF6gxjEnlmuGrJXVbNuzT9qBBavbLwCsOGabYfZo0T0to5eqruptLy" crossorigin="anonymous"></script>
	</body>
</html>