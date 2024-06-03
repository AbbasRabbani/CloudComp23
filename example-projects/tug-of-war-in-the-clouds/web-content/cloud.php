<?php
session_start();
include 'config.php';
?>
<link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
<script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js" integrity="sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1" crossorigin="anonymous"></script>
<script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js" integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM" crossorigin="anonymous"></script>

<?php
if (!isset($_SESSION["team"]))
{
   if (isset($_POST["team_minus"]))
   {
      print "You joined team minus (blue)...";
      $_SESSION["team"]="minus";
   }
   elseif (isset($_POST["team_plus"]))
   {
      print "You joined team minus (green)...";
      $_SESSION["team"]="plus";
   }
   else
   {
      print "<h1>Choose your team!</h1>";
      ?>
      <form action="" method="post">
      <input type="submit" name="team_minus" value="Team Minus (Blue)">
      <input type="submit" name="team_plus" value="Team Plus (Green)">
      </form>
      <?php
   }
}

if (isset($_SESSION["team"]))
{
   ?>

   <h1>Pull!!!</h1>
   <p>
   <?php
   if (isset($_GET['cloud_id']))
   {
      $sql = "SELECT * FROM clouds WHERE cloud_id = " . $_GET['cloud_id'];
      foreach ($pdo->query($sql) as $row)
      {
         if (abs(intval($row["value"])) >= intval($row["max_value"]))
         {
            unset($_SESSION["team"]);
            $_SESSION["finished"] = true;
         }
      }

      if (isset($_POST['pull']))
      {
         if ($_SESSION["team"] == "plus")
         {
            print "You pulled for team plus (green)...";
            $sql = "UPDATE clouds SET value=value+1 WHERE cloud_id = " . $_GET['cloud_id'];
            $result = $pdo->query($sql);
         }
         if ($_SESSION["team"] == "minus")
         {
            print "You pulled for team minus (blue)...";   
            $sql = "UPDATE clouds SET value=value-1 WHERE cloud_id = " . $_GET['cloud_id'];
            $result = $pdo->query($sql);
         }
      }

      $sql = "SELECT * FROM clouds WHERE cloud_id = " . $_GET['cloud_id'];
      foreach ($pdo->query($sql) as $row)
      {
         print "<h2>Value: " . $row["value"] . " (Goal: " . $row["max_value"] . ")</h2>";
      }
      
      if (!isset($_SESSION["finished"]))
      {
         ?>
         <form action="" method="post">
            <input type="submit" name="pull" value="Pull">
         </form>
         <?php
      }
      else
      {
         print "<h2>game over</h2>";
         if (intval($row["value"] == intval($row["max_value"])))
         {
            print "Team plus (green) won!";
         }
         else
         {
            print "Team minus (blue) won!";
         }
         session_destroy();
      }
   }
}
?>
<br />
<a href='index.php'>Leave Game</a>
