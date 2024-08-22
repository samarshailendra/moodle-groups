# UpdateGroupsInMoodle and Reporting



## Getting started

To make it easy for you to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

- [ ] [Create](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#create-a-file) or [upload](https://docs.gitlab.com/ee/user/project/repository/web_editor.html#upload-a-file) files
- [ ] [Add files using the command line](https://docs.gitlab.com/ee/gitlab-basics/add-file.html#add-a-file-using-the-command-line) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/mit_automation/updategroupsinmoodle.git
git branch -M main
git push -uf origin main

For this repository to work, Install google chrome and ChromeDriver to automate the browser.
```

## How to Use

- [ ] UpdateGroupsInMoodle 
1. Create the groups for your unit using the import groups file option in Moodle.
2. Update the Units.csv file with the unit id and the corresponding unique identifier in Moodle.
3. Create the <unit_id>_groups.csv with the group name followed by student id. Note that group should be pre-exisitng in the moodle. 
4. Run the updategroupinmoodle executable in the dist folder and follow the onscreen instructions.

- [ ] Report AMS
1. Create the AMS_Units.csv with the unit name and the unique unit id for your own group in the AMS. Note that there can be mulitple unit ids belonging to each person for a unit.
2. Run the reportams executable in the dist folder and follow the onscreen instructions.
3. The status logs are created in the app.log file. And most of the errors are displayed on screen. 


***
## Author

Dr. Samar Shailendrda

## License
These tools are distributed under GPL v3.0.
