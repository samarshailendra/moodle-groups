# UpdateGroupsInMoodle and Reporting

These are fun projects and you can expect the bugs and errors in it. Feel to update the source code by yourself or report it back for updates in future.


## Pre-requisites

1. Clone the repository using git clone. Or download the executable from the dist folder manually.
2. Download the correct Windows or Linux release package. It includes Chromium and all application dependencies, so users do not install a browser, ChromeDriver, Python, or other software.
3. When running the Python source rather than the release package, install its dependency with `python3 -m pip install -r requirements.txt` and run `PLAYWRIGHT_BROWSERS_PATH=0 python3 -m playwright install chromium`.


## How to Use

- [ ] UpdateGroupsInMoodle 
1. Create the groups for your unit using the import groups file option in Moodle.
2. Run **UnitsAndGroups**. It opens its bundled Chromium browser so you can complete your normal Moodle OAuth or username/password login.
3. For each unit, enter its unit code, Moodle unit ID, and CSV file. The default CSV file name is `<UnitCode>.csv`; for example, `MITS5001.csv`.
4. The CSV can use either `GroupName,StudentId,StudentId,...` (one group per row) or repeated `GroupName,StudentId` rows. An optional `GroupName,StudentId` header is accepted. Every group must already exist in Moodle; the program stops before changing members if a CSV group is missing.
5. After a unit is complete, choose whether to process another unit.

## Creating releases

Push a version tag such as `v1.0.0`. The **Build release packages** workflow creates
native Windows and Linux executables with bundled Chromium, then attaches them to the
GitHub release. Users download the executable for their operating system and supply
only their CSV file.

- [ ] Reporting
1. Create the AMS_Units.csv with the unit name and the unique unit id for your own group in the system. Note that there can be mulitple unit ids belonging to each person for a unit.
2. Run the **reportAMS** executable in the **dist/Linux** folder and follow the onscreen instructions.
3. The status logs are created in the app.log file. And most of the errors are displayed on screen. 

***
## Author

Dr. Samar Shailendrda

## License
These tools are distributed under GPL v3.0.
