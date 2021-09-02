-- MySQL dump 10.19  Distrib 10.3.29-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: flawlessdbdev
-- ------------------------------------------------------
-- Server version	10.3.29-MariaDB-0+deb10u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Countries`
--

DROP TABLE IF EXISTS `Countries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Countries` (
  `id` varchar(10) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Countries`
--

LOCK TABLES `Countries` WRITE;
/*!40000 ALTER TABLE `Countries` DISABLE KEYS */;
INSERT INTO `Countries` VALUES (':AC:'),(':AD:'),(':AE:'),(':AF:'),(':AG:'),(':AI:'),(':AL:'),(':AM:'),(':AO:'),(':AQ:'),(':AR:'),(':AS:'),(':AT:'),(':AU:'),(':AW:'),(':AX:'),(':AZ:'),(':BA:'),(':BB:'),(':BD:'),(':BE:'),(':BF:'),(':BG:'),(':BH:'),(':BI:'),(':BJ:'),(':BL:'),(':BM:'),(':BN:'),(':BO:'),(':BQ:'),(':BR:'),(':BS:'),(':BT:'),(':BV:'),(':BW:'),(':BY:'),(':BZ:'),(':CA:'),(':CC:'),(':CD:'),(':CF:'),(':CG:'),(':CH:'),(':CI:'),(':CK:'),(':CL:'),(':CM:'),(':CN:'),(':CO:'),(':CP:'),(':CR:'),(':CU:'),(':CV:'),(':CW:'),(':CX:'),(':CY:'),(':CZ:'),(':DE:'),(':DG:'),(':DJ:'),(':DK:'),(':DM:'),(':DO:'),(':DZ:'),(':EA:'),(':EC:'),(':EE:'),(':EG:'),(':EH:'),(':ER:'),(':ES:'),(':ET:'),(':EU:'),(':FI:'),(':FJ:'),(':FK:'),(':FM:'),(':FO:'),(':FR:'),(':GA:'),(':GB:'),(':GD:'),(':GE:'),(':GF:'),(':GG:'),(':GH:'),(':GI:'),(':GL:'),(':GM:'),(':GN:'),(':GP:'),(':GQ:'),(':GR:'),(':GS:'),(':GT:'),(':GU:'),(':GW:'),(':GY:'),(':HK:'),(':HM:'),(':HN:'),(':HR:'),(':HT:'),(':HU:'),(':IC:'),(':ID:'),(':IE:'),(':IL:'),(':IM:'),(':IN:'),(':IO:'),(':IQ:'),(':IR:'),(':IS:'),(':IT:'),(':JE:'),(':JM:'),(':JO:'),(':JP:'),(':KE:'),(':KG:'),(':KH:'),(':KI:'),(':KM:'),(':KN:'),(':KP:'),(':KR:'),(':KW:'),(':KY:'),(':KZ:'),(':LA:'),(':LB:'),(':LC:'),(':LI:'),(':LK:'),(':LR:'),(':LS:'),(':LT:'),(':LU:'),(':LV:'),(':LY:'),(':MA:'),(':MC:'),(':MD:'),(':ME:'),(':MF:'),(':MG:'),(':MH:'),(':MK:'),(':ML:'),(':MM:'),(':MN:'),(':MO:'),(':MP:'),(':MQ:'),(':MR:'),(':MS:'),(':MT:'),(':MU:'),(':MV:'),(':MW:'),(':MX:'),(':MY:'),(':MZ:'),(':NA:'),(':NC:'),(':NE:'),(':NF:'),(':NG:'),(':NI:'),(':NL:'),(':NO:'),(':NP:'),(':NR:'),(':NU:'),(':NZ:'),(':OM:'),(':PA:'),(':PE:'),(':PF:'),(':PG:'),(':PH:'),(':PK:'),(':PL:'),(':PM:'),(':PN:'),(':PR:'),(':PS:'),(':PT:'),(':PW:'),(':PY:'),(':QA:'),(':RE:'),(':RO:'),(':RS:'),(':RU:'),(':RW:'),(':SA:'),(':SB:'),(':SC:'),(':SD:'),(':SE:'),(':SG:'),(':SH:'),(':SI:'),(':SJ:'),(':SK:'),(':SL:'),(':SM:'),(':SN:'),(':SO:'),(':SR:'),(':SS:'),(':ST:'),(':SV:'),(':SX:'),(':SY:'),(':SZ:'),(':TA:'),(':TC:'),(':TD:'),(':TF:'),(':TG:'),(':TH:'),(':TJ:'),(':TK:'),(':TL:'),(':TM:'),(':TN:'),(':TO:'),(':TR:'),(':TT:'),(':TV:'),(':TW:'),(':TZ:'),(':UA:'),(':UG:'),(':UM:'),(':UN:'),(':US:'),(':UY:'),(':UZ:'),(':VA:'),(':VC:'),(':VE:'),(':VG:'),(':VI:'),(':VN:'),(':VU:'),(':WF:'),(':WS:'),(':XK:'),(':YE:'),(':YT:'),(':ZA:'),(':ZM:'),(':ZW:');
/*!40000 ALTER TABLE `Countries` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Cups`
--

DROP TABLE IF EXISTS `Cups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Cups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) DEFAULT NULL,
  `number_of_teams` int(11) DEFAULT NULL,
  `status` tinyint(4) DEFAULT NULL,
  `signup_message_id` varchar(50) DEFAULT NULL,
  `signup_start_date` varchar(50) DEFAULT NULL,
  `signup_end_date` varchar(50) DEFAULT NULL,
  `mini_roster` tinyint(4) DEFAULT NULL,
  `category_id` varchar(50) DEFAULT NULL,
  `chan_admin_id` varchar(50) DEFAULT NULL,
  `chan_signups_id` varchar(50) DEFAULT NULL,
  `chan_calendar_id` varchar(50) DEFAULT NULL,
  `chan_stage_id` varchar(50) DEFAULT NULL,
  `category_match_schedule_id` varchar(50) DEFAULT NULL,
  `chan_match_index_id` varchar(50) DEFAULT NULL,
  `maxi_roster` int(11) DEFAULT NULL,
  `match_index_embed_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Cups`
--

LOCK TABLES `Cups` WRITE;
/*!40000 ALTER TABLE `Cups` DISABLE KEYS */;
INSERT INTO `Cups` VALUES (7,'UTCS I',NULL,NULL,'882445117795999755','2021-08-01 00:00:00','2021-10-01 00:00:00',1,'882444907380359178','882444910148583434','882444913059455008','882444913625661520','882444914326134794','882444914682626108','882444914783318047',8,NULL);
/*!40000 ALTER TABLE `Cups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Divisions`
--

DROP TABLE IF EXISTS `Divisions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Divisions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cup_id` int(11) DEFAULT NULL,
  `div_number` int(11) DEFAULT NULL,
  `embed_id` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Divisions`
--

LOCK TABLES `Divisions` WRITE;
/*!40000 ALTER TABLE `Divisions` DISABLE KEYS */;
/*!40000 ALTER TABLE `Divisions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Fixtures`
--

DROP TABLE IF EXISTS `Fixtures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Fixtures` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cup_id` int(11) DEFAULT NULL,
  `team1` varchar(50) DEFAULT NULL,
  `team2` varchar(50) DEFAULT NULL,
  `format` varchar(10) DEFAULT NULL,
  `channel_id` varchar(50) DEFAULT NULL,
  `date` varchar(50) DEFAULT NULL,
  `embed_id` varchar(50) DEFAULT NULL,
  `status` tinyint(4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Fixtures`
--

LOCK TABLES `Fixtures` WRITE;
/*!40000 ALTER TABLE `Fixtures` DISABLE KEYS */;
INSERT INTO `Fixtures` VALUES (3,7,'13','16','BO3','882699945126297681','2021-08-01 21:00:00','882699947487682590',1);
/*!40000 ALTER TABLE `Fixtures` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Maps`
--

DROP TABLE IF EXISTS `Maps`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Maps` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) DEFAULT NULL,
  `gamemode` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Maps`
--

LOCK TABLES `Maps` WRITE;
/*!40000 ALTER TABLE `Maps` DISABLE KEYS */;
INSERT INTO `Maps` VALUES (1,'Austria','TS'),(2,'Casa','TS'),(3,'Kingdom','TS'),(4,'Tohunga','TS'),(5,'Abbey','CTF'),(6,'Algiers','CTF'),(7,'Tohunga','CTF'),(8,'Turnpike','CTF');
/*!40000 ALTER TABLE `Maps` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Roster`
--

DROP TABLE IF EXISTS `Roster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Roster` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `team_id` int(11) DEFAULT NULL,
  `player_id` int(11) DEFAULT NULL,
  `accepted` tinyint(4) DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Roster`
--

LOCK TABLES `Roster` WRITE;
/*!40000 ALTER TABLE `Roster` DISABLE KEYS */;
INSERT INTO `Roster` VALUES (8,5,2,1),(15,7,23,2),(16,7,6,1),(17,8,24,2),(18,5,14,2),(19,5,21,1),(20,5,20,1),(21,5,22,1),(23,5,27,1),(24,9,25,2),(25,10,28,2),(26,8,29,1),(27,5,30,1),(28,8,32,1),(32,11,34,2),(33,9,22,1),(34,13,14,2),(35,14,6,2),(42,16,39,2),(43,13,39,3),(44,17,14,2),(45,18,14,2),(46,5,6,1),(47,5,39,1),(48,5,31,1);
/*!40000 ALTER TABLE `Roster` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Signups`
--

DROP TABLE IF EXISTS `Signups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Signups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cup_id` int(11) DEFAULT NULL,
  `team_id` int(11) DEFAULT NULL,
  `div_number` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Signups`
--

LOCK TABLES `Signups` WRITE;
/*!40000 ALTER TABLE `Signups` DISABLE KEYS */;
INSERT INTO `Signups` VALUES (22,7,13,NULL),(23,7,16,NULL);
/*!40000 ALTER TABLE `Signups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Teams`
--

DROP TABLE IF EXISTS `Teams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Teams` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(50) DEFAULT NULL,
  `tag` varchar(50) DEFAULT NULL,
  `country` varchar(50) DEFAULT NULL,
  `captain` varchar(50) DEFAULT NULL,
  `number_of_players` int(11) DEFAULT 1,
  `roster_message_id` varchar(50) DEFAULT NULL,
  `role_id` varchar(50) DEFAULT NULL,
  `discord_link` varchar(50) DEFAULT 'None',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Teams`
--

LOCK TABLES `Teams` WRITE;
/*!40000 ALTER TABLE `Teams` DISABLE KEYS */;
INSERT INTO `Teams` VALUES (5,'No way','now`',':FR:','14',1,'879377009988497409','878373236109344789','https://discord.gg/ENyENX3Dhu'),(7,'Shichibukai','shk.',':EU:','23',1,'879377013654302793','879017813728178216','None'),(8,'Wasted Goats','wG*',':EU:','24',1,'879377017601155144','879018110542311434','https://discord.gg/juwFez4'),(9,'b00bs','[b00bs]',':MK:','25',1,'879377020516204575','879024952781733908','https://discord.gg/k9PDTTy'),(10,'Idle','Idle',':CP:','28',1,'879377023846465536','879027962354217050','None'),(11,'Thomas & Friends','t&f',':US:','34',1,'879377031647879219','879231331731644427','None'),(13,'||test|| **formatage** _coucou_','||holy||',':US:','14',1,'879749951134007346','879749916925263932','None'),(14,'Ernest Is The Best','ernBest|',':BE:','6',1,'879811463169077328','879811425961402399','None'),(16,'la tim de nao','.nao',':FR:','39',1,'879923283036876881','879923229874065518','None'),(17,'la tim de holy','.holy',':FR:','14',1,'880533603916873790','880533524808093707','None'),(18,'la tim de holy2','.holy2',':FR:','14',1,'880533690957049926','880533606680920084','None');
/*!40000 ALTER TABLE `Teams` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Users`
--

DROP TABLE IF EXISTS `Users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Users` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `discord_id` varchar(50) DEFAULT NULL,
  `urt_auth` varchar(50) DEFAULT NULL,
  `ingame_name` varchar(50) DEFAULT NULL,
  `country` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=40 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Users`
--

LOCK TABLES `Users` WRITE;
/*!40000 ALTER TABLE `Users` DISABLE KEYS */;
INSERT INTO `Users` VALUES (2,'158529423656615938','st0mp','st0mP',':FR:'),(6,'160806173950345216','r0cket','Rocket',':BE:'),(11,'205821831964393472','Zmb','Zmb',':FR:'),(14,'299884015308242954','holycrap','Holycrap',':US:'),(20,'146975425812234241','urumi','Sukina',':FR:'),(21,'284563925544992769','arnica','arni',':FR:'),(22,'293662664931147776','breeyyy','breey',':FR:'),(23,'276129625745260564','wickedd','Memnon',':PT:'),(24,'536612891672182794','feskarn','feskarn',':SE:'),(25,'117620974806892549','Biddle','Biddle',':FR:'),(26,'450849663629656065','Delirium','Delirium',':NZ:'),(27,'383732237222543392','usopp','Usopp',':FR:'),(28,'508080527685844997','Lytchi','lytchi',':FR:'),(29,'323806047997526020','rkq','rkq',':FI:'),(30,'157623793357946880','pixmachine','PiXieS',':FR:'),(31,'388023415421927424','ernestofficial','Ernest',':BE:'),(32,'182955516123807744','dems','DeMS',':EA:'),(34,'267805697662648321','thomasewarfare','ThomasE-Warfare',':US:'),(35,'160390216375336961','maku','Maku',':GB:'),(36,'162678389856010240','Logic','logic',':BE:'),(39,'837163338818912266','naomii','HolycrapLeDeux',':FR:');
/*!40000 ALTER TABLE `Users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2021-09-02  3:22:37
