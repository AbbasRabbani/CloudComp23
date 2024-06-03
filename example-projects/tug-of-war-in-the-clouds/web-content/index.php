<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
<script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js" integrity="sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1" crossorigin="anonymous"></script>
<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js" integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM" crossorigin="anonymous"></script>
<h1>Welcome to "tug of war in the clouds"!</h1>
<p>
Choose and tug a cloud:
</p>
<p>
<?php
include 'config.php';

if (isset($_POST['new_cloud_name']))
{
   $sql = "INSERT INTO clouds (name, value, max_value) VALUES ('" . $_POST['new_cloud_name'] . "',0," . $_POST['new_cloud_goal'] . ")";
   $pdo->query($sql);
}
 
$sql = "SELECT * FROM clouds";
foreach ($pdo->query($sql) as $row) {
   if (abs(intval($row['value'])) < intval($row['max_value']))
   {
      echo "<a href='cloud.php?cloud_id=" . $row['cloud_id'] . "'>" . $row['name'] . "</a> (score: " . $row['value'] . ", goal:" . $row['max_value'] . ")<br />";
   }
}
?>
<!-- list -->
</p>
<p>
or form a new cloud: 
<form action="" method="post">
Name: <input name="new_cloud_name" value="">
Goal: <input name="new_cloud_goal" value="10">
<input type="submit" value="Create">
</form>
</p>