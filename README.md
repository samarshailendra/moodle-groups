# UpdateGroupsInMoodle and Reporting

These are fun projects and you can expect the bugs and errors in it. Feel to update the source code by yourself or report it back for updates in future.


## Pre-requisites

1. Clone the repository using git clone. Or download the executable from the dist folder manually.
2. For this repository to work, Install google chrome and ChromeDriver to automate the browser.


## How to Use

- [ ] UpdateGroupsInMoodle 
1. Create the groups for your unit using the import groups file option in Moodle.
2. Update the Units.csv file with the unit id and the corresponding unique identifier in Moodle.
3. Create the <unit_id>_groups.csv with the group name followed by student id. Note that group should be pre-exisitng in the moodle. 
4. Run the **updateGroupInMoodle** executable in the **dist/Linux** folder and follow the onscreen instructions.

- [ ] Reporting
1. Create the AMS_Units.csv with the unit name and the unique unit id for your own group in the system. Note that there can be mulitple unit ids belonging to each person for a unit.
2. Run the **reportAMS** executable in the **dist/Linux** folder and follow the onscreen instructions.
3. The status logs are created in the app.log file. And most of the errors are displayed on screen. 

***
## Author

Dr. Samar Shailendrda

## License
These tools are distributed under GPL v3.0.
