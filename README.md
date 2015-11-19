# Auto-Validation
This is a route auto-validation for SenSG project.

## Environment Configuration

###Install the xlrd and googlemaps (Ubuntu 14.04)
The packet is for excel file.
>sudo pip install xlrd

The packet is for google API 
>sudo pip install -U googlemaps

The packet is for log file
>sudo pip install colored

The packet is for map visualization
>sudo pip install pygmaps

If you have any problem with these packets, please let me konw or google it.

##Format
###Input File Format
- Column 1: Node ID
- Column 2: date
- Column 3: home lat
- Column 4: home lon
- Column 5: school lat
- Column 6: school lon

##Tutorial
###How to use
- You can refer to the *def main()* to see how to use these class and get the information you need.
- You can extend the class, if you want to more information or more functions,
- For visualization part, you can visualize a route path. Open the file "mypage.html" in the browser and you can see the green path.

### How to run
>python GetDataFromGoogleAPI.py

### Further improvement
- Please build a new class for route comparison.
- I do not finish the part of getting the data from the our database.</br>You can finish this part refer to the previous hand check code.




 
