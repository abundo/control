#!/usr/bin/php
<?php
//
//  apt install php-soap php-yaml
//

define("CONFIG_FILE", "/etc/abcontrol/abcontrol.yaml");

$config = yaml_parse_file(CONFIG_FILE);

$oid = 1;
// $oid = 290710;
// $oid = 108871;

$url = $config["becs"]["eapi"]["url"];
$username = $config["becs"]["eapi"]["username"];
$password = $config["becs"]["eapi"]["password"];

if (count($argv) == 2) {
    $oid = $argv[1];
}

$client = new SoapClient($url);

$r = $client->sessionLogin( array(
    "username" => $username,
    "password" => $password,
    ));
$sessionid = $r->sessionid;

$headers = array();

$soapStruct = new SoapVar(array("sessionid" => $sessionid), SOAP_ENC_OBJECT);
$headers[] = new SoapHeader($url, 'request', $soapStruct, false);

$client->__setSoapHeaders($headers);

$data = $client->objectTreeFind(
            array(
                "oid" => $oid,
                "classmask" => "element-attach,interface,resource-inet",
                "walkdown" => 0,
            )
        );
print(json_encode($data));
$r = $client->sessionLogout();
