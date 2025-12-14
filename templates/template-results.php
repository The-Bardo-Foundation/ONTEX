<?php /* Template Name: Result Page */ get_header( ); $page_id = get_the_id();
$search_query = "";
$search_query = "Osteosarcoma";
$country = "";
$city = "";
$status = [];
$phase = [];
$type = [];
$term = "";
$age = [];
$sort = "";
$trial_id = "";
$min_rnk = 1;
$max_rnk = 10;
$page_no = 1;
// if(!empty($_REQUEST['phase'])) {
    // foreach($_REQUEST['phase'] as $phasee) {
            // echo $phasee; 
    // }
// } 
 // echo "<pre>"; print_r($_REQUEST); echo "</pre>";
if(isset($_REQUEST['term']) && $_REQUEST['term'] != ""){
	$term = $_REQUEST['term'];
	$search_query = $_REQUEST['term'];
}
if(isset($_REQUEST['city']) && $_REQUEST['city'] != ""){
	$city = $_REQUEST['city'];
	// $search_query .= " AND AREA[LocationCountry]$country";
	$search_query .= "&city=$city";
}
if(isset($_REQUEST['country']) && $_REQUEST['country'] != ""){
	$country = $_REQUEST['country'];
	// $search_query .= " AND AREA[LocationCountry]$country";
	$search_query .= "&country=$country";
}
if(isset($_REQUEST['status']) && $_REQUEST['status'] != ""){
	$status = $_REQUEST['status'];
	if(!empty($_REQUEST['status'])) {
		$ci = 1;
		foreach($_REQUEST['status'] as $singlestatus) {
				if($ci>1) $statuslist .= ",$singlestatus"; else $statuslist = $singlestatus;
		$ci++; }
	} 
	$search_query .= "&status=$statuslist";
	// $search_query .= " AND AREA[OverallStatus]$status AND COVERAGE[FullMatch]$status";
	// $search_query .= "&status=$status";
} 
if(isset($_REQUEST['phase']) && $_REQUEST['phase'] != ""){
	$phase = $_REQUEST['phase'];
	if(!empty($_REQUEST['phase'])) {
		$ci = 1;
		foreach($_REQUEST['phase'] as $singlephase) {
				if($ci>1) $phaselist .= ",$singlephase"; else $phaselist = $singlephase;
		$ci++; }
	} 
	$search_query .= "&phase=$phaselist";
	// $search_query .= " AND AREA[Phase]$phase";
}
// echo $phaselist;
if(isset($_REQUEST['type']) && $_REQUEST['type'] != ""){
	$type = $_REQUEST['type'];
	if(!empty($_REQUEST['type'])) {
		$ci = 1;
		foreach($_REQUEST['type'] as $singletype) {
				if($ci>1) $typelist .= ",$singletype"; else $typelist = $singletype;
		$ci++; }
	} 
	$search_query .= "&type=$typelist";
	// $search_query .= " AND AREA[StudyType]$type"; 
	// $search_query .= "&type=$type";
}
if(isset($_REQUEST['age']) && $_REQUEST['age'] != ""){
	$age = $_REQUEST['age'];
	if(!empty($_REQUEST['age'])) {
		$ci = 1;
		foreach($_REQUEST['age'] as $singleage) {
				if($ci>1) $agelist .= ",$singleage"; else $agelist = $singleage;
		$ci++; }
	} 
	$search_query .= "&age=$agelist";
	// $search_query .= " AND AREA[StdAge]$age"; 
	// $search_query .= "&age=$age";
}
if(isset($_REQUEST['sort']) && $_REQUEST['sort'] != ""){
	$sort = $_REQUEST['sort'];
	// $search_query .= " AND AREA[StdAge]$age"; 
	$search_query .= "&sort=$sort";
}
if(isset($_REQUEST['trial_id']) && $_REQUEST['trial_id'] != ""){
	$trial_id = $_REQUEST['trial_id'];
	// $search_query .= " AND AREA[NCTId]$trail_id"; 
	$search_query .= "&trail_id=$trial_id";
}
if(isset($_REQUEST['page_no']) && $_REQUEST['page_no'] != ""){
	$page_no = $_REQUEST['page_no'];
	$min_rnk = ($page_no - 1)*10;
	// $max_rnk = $page_no*10;
	$max_rnk = 10;
}
$url = str_replace(" ","+","https://clinicaltrials.gov/api/query/study_fields?expr=$search_query&fields=StudyType,OfficialTitle,Phase,OverallStatus,LocationCountry,StdAge,NCTId,BriefSummary&fmt=JSON&min=$min_rnk&max=$max_rnk");
// echo $url;
$curl = curl_init();
curl_setopt_array($curl, array(
  CURLOPT_URL => $url,
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_TIMEOUT => 30,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => "GET",
  CURLOPT_HTTPHEADER => array(
    "cache-control: no-cache"
  ),
));
$response = curl_exec($curl);
$err = curl_error($curl);

curl_close($curl); 
$arrres = json_decode($response);
$study_fieslds = $arrres->StudyFieldsResponse->StudyFields;
//echo "<pre>";print_r($arrres->StudyFieldsResponse->NStudiesFound);echo "</pre>";

$urll = str_replace(" ","+","http://jayr57.sg-host.com/api/get-trail?term=$search_query&min=$min_rnk");
  // echo $urll;
$curll = curl_init();
curl_setopt_array($curll, array(
  CURLOPT_URL => $urll, 
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_TIMEOUT => 30,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => "GET",
  CURLOPT_HTTPHEADER => array(
    "cache-control: no-cache" 
  ),
));
$responsee = curl_exec($curll); 
$errr = curl_error($curll);

curl_close($curll); 
$arrress = json_decode($responsee);
// echo "Record: <pre>"; print_r($arrress); echo "</pre>";
?>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
<div class="container">
	<div class="row">
		<div class="col-12">
			<h1>Result</h1>
		</div>
	</div>
	<div class="row">
		<div class="col-md-3">
			<!-- Sidebar filter section -->
			<section id="database_filter">
				<form class="result_form" action="" method="GET">
					<input type="hidden" name="country" value="<?php echo $country; ?>" />
					<!-- <input type="hidden" name="trial_id" value="<?php //echo $trial_id; ?>" /> -->
					<div class="py-2 ml-3">
						<div class="form-group">
							<input type="submit" class="result_submit btn btn-primary" value="Apply">
							<a href="/result/" class="clear_submit btn btn-secondary">Clear</a>
						</div>
					</div>
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold">Age</h6>
							<div class="form-group"> <input type="checkbox" class="age" name="age[]" value="Child" <?php if(in_array("Child", $age)) echo 'checked'; ?>> <label for="Child">Child (Under 18)</label> </div>
							<div class="form-group"> <input type="checkbox" class="age" name="age[]" value="Adult" <?php if(in_array("Adult", $age)) echo 'checked'; ?>> <label for="Adult">Adult (18–64)</label> </div>
							<div class="form-group"> <input type="checkbox" class="age" name="age[]" value="Older Adult" <?php if(in_array("Older Adult", $age)) echo 'checked'; ?>> <label for="Older Adult">Older Adult (65+)</label> </div>
					</div>
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold">Country</h6>
						<select id="countries" name="country" value="<?php echo $country; ?>" class="country_select searchable_select">
							<option value="">Select a country…</option>
							<option value="Afghanistan" <?php if($country =="Afghanistan") echo 'selected'; ?>>Afghanistan</option>
							<option value="Åland Islands" <?php if($country =="Åland Islands") echo 'selected'; ?>>Åland Islands</option>
							<option value="Albania" <?php if($country =="Albania") echo 'selected'; ?>>Albania</option>
							<option value="Algeria" <?php if($country =="Algeria") echo 'selected'; ?>>Algeria</option>
							<option value="American Samoa" <?php if($country =="American Samoa") echo 'selected'; ?>>American Samoa</option>
							<option value="Andorra" <?php if($country =="Andorra") echo 'selected'; ?>>Andorra</option>
							<option value="Angola" <?php if($country =="Angola") echo 'selected'; ?>>Angola</option>
							<option value="Anguilla" <?php if($country =="Anguilla") echo 'selected'; ?>>Anguilla</option>
							<option value="Antarctica" <?php if($country =="Antarctica") echo 'selected'; ?>>Antarctica</option>
							<option value="Antigua and Barbuda" <?php if($country =="Antigua and Barbuda") echo 'selected'; ?>>Antigua and Barbuda</option>
							<option value="Argentina" <?php if($country =="Argentina") echo 'selected'; ?>>Argentina</option>
							<option value="Armenia" <?php if($country =="Armenia") echo 'selected'; ?>>Armenia</option>
							<option value="Aruba" <?php if($country =="Aruba") echo 'selected'; ?>>Aruba</option>
							<option value="Australia" <?php if($country =="Australia") echo 'selected'; ?>>Australia</option>
							<option value="Austria" <?php if($country =="Austria") echo 'selected'; ?>>Austria</option>
							<option value="Azerbaijan" <?php if($country =="Azerbaijan") echo 'selected'; ?>>Azerbaijan</option>
							<option value="Bahamas" <?php if($country =="Bahamas") echo 'selected'; ?>>Bahamas</option>
							<option value="Bahrain" <?php if($country =="Bahrain") echo 'selected'; ?>>Bahrain</option>
							<option value="Bangladesh" <?php if($country =="Bangladesh") echo 'selected'; ?>>Bangladesh</option>
							<option value="Barbados" <?php if($country =="Barbados") echo 'selected'; ?>>Barbados</option>
							<option value="Belarus" <?php if($country =="Belarus") echo 'selected'; ?>>Belarus</option>
							<option value="Belgium" <?php if($country =="Belgium") echo 'selected'; ?>>Belgium</option>
							<option value="Belize" <?php if($country =="Belize") echo 'selected'; ?>>Belize</option>
							<option value="Benin" <?php if($country =="Benin") echo 'selected'; ?>>Benin</option>
							<option value="Bermuda" <?php if($country =="Bermuda") echo 'selected'; ?>>Bermuda</option>
							<option value="Bhutan" <?php if($country =="Bhutan") echo 'selected'; ?>>Bhutan</option>
							<option value="Bolivia" <?php if($country =="Bolivia") echo 'selected'; ?>>Bolivia</option>
							<option value="Bosnia and Herzegovina" <?php if($country =="Bosnia and Herzegovina") echo 'selected'; ?>>Bosnia and Herzegovina</option>
							<option value="Botswana" <?php if($country =="Botswana") echo 'selected'; ?>>Botswana</option>
							<option value="Bouvet Island" <?php if($country =="Bouvet Island") echo 'selected'; ?>>Bouvet Island</option>
							<option value="Brazil" <?php if($country =="Brazil") echo 'selected'; ?>>Brazil</option>
							<option value="British Indian Ocean Territory" <?php if($country =="British Indian Ocean Territory") echo 'selected'; ?>>British Indian Ocean Territory</option>
							<option value="Brunei Darussalam" <?php if($country =="Brunei Darussalam") echo 'selected'; ?>>Brunei Darussalam</option>
							<option value="Bulgaria" <?php if($country =="Bulgaria") echo 'selected'; ?>>Bulgaria</option>
							<option value="Burkina Faso" <?php if($country =="Burkina Faso") echo 'selected'; ?>>Burkina Faso</option>
							<option value="Burundi" <?php if($country =="Burundi") echo 'selected'; ?>>Burundi</option>
							<option value="Cambodia" <?php if($country =="Cambodia") echo 'selected'; ?>>Cambodia</option>
							<option value="Cameroon" <?php if($country =="Cameroon") echo 'selected'; ?>>Cameroon</option>
							<option value="Canada" <?php if($country =="Canada") echo 'selected'; ?>>Canada</option>
							<option value="Cape Verde" <?php if($country =="Cape Verde") echo 'selected'; ?>>Cape Verde</option>
							<option value="Cayman Islands" <?php if($country =="Cayman Islands") echo 'selected'; ?>>Cayman Islands</option>
							<option value="Central African Republic" <?php if($country =="Central African Republic") echo 'selected'; ?>>Central African Republic</option>
							<option value="Chad" <?php if($country =="Chad") echo 'selected'; ?>>Chad</option>
							<option value="Chile" <?php if($country =="Chile") echo 'selected'; ?>>Chile</option>
							<option value="China" <?php if($country =="China") echo 'selected'; ?>>China</option>
							<option value="Christmas Island" <?php if($country =="Christmas Island") echo 'selected'; ?>>Christmas Island</option>
							<option value="Cocos (Keeling) Islands" <?php if($country =="Cocos (Keeling) Islands") echo 'selected'; ?>>Cocos (Keeling) Islands</option>
							<option value="Colombia" <?php if($country =="Colombia") echo 'selected'; ?>>Colombia</option>
							<option value="Comoros" <?php if($country =="Comoros") echo 'selected'; ?>>Comoros</option>
							<option value="Congo" <?php if($country =="Congo") echo 'selected'; ?>>Congo</option>
							<option value="Congo, The Democratic Republic of The" <?php if($country =="Congo, The Democratic Republic of The") echo 'selected'; ?>>Congo, The Democratic Republic of The</option>
							<option value="Cook Islands" <?php if($country =="Cook Islands") echo 'selected'; ?>>Cook Islands</option>
							<option value="Costa Rica" <?php if($country =="Costa Rica") echo 'selected'; ?>>Costa Rica</option>
							<option value="Cote D'ivoire" <?php if($country =="Cote D'ivoire") echo 'selected'; ?>>Cote D’ivoire</option>
							<option value="Croatia" <?php if($country =="Croatia") echo 'selected'; ?>>Croatia</option>
							<option value="Cuba" <?php if($country =="Cuba") echo 'selected'; ?>>Cuba</option>
							<option value="Cyprus" <?php if($country =="Cyprus") echo 'selected'; ?>>Cyprus</option>
							<option value="Czech Republic" <?php if($country =="Czech Republic") echo 'selected'; ?>>Czech Republic</option>
							<option value="Denmark" <?php if($country =="Denmark") echo 'selected'; ?>>Denmark</option>
							<option value="Djibouti" <?php if($country =="Djibouti") echo 'selected'; ?>>Djibouti</option>
							<option value="Dominica" <?php if($country =="Dominica") echo 'selected'; ?>>Dominica</option>
							<option value="Dominican Republic" <?php if($country =="Dominican Republic") echo 'selected'; ?>>Dominican Republic</option>
							<option value="Ecuador" <?php if($country =="Ecuador") echo 'selected'; ?>>Ecuador</option>
							<option value="Egypt" <?php if($country =="Egypt") echo 'selected'; ?>>Egypt</option>
							<option value="El Salvador" <?php if($country =="El Salvador") echo 'selected'; ?>>El Salvador</option>
							<option value="Equatorial Guinea" <?php if($country =="Equatorial Guinea") echo 'selected'; ?>>Equatorial Guinea</option>
							<option value="Eritrea" <?php if($country =="Eritrea") echo 'selected'; ?>>Eritrea</option>
							<option value="Estonia" <?php if($country =="Estonia") echo 'selected'; ?>>Estonia</option>
							<option value="Ethiopia" <?php if($country =="Ethiopia") echo 'selected'; ?>>Ethiopia</option>
							<option value="Falkland Islands (Malvinas)" <?php if($country =="Falkland Islands (Malvinas)") echo 'selected'; ?>>Falkland Islands (Malvinas)</option>
							<option value="Faroe Islands" <?php if($country =="Faroe Islands") echo 'selected'; ?>>Faroe Islands</option>
							<option value="Fiji" <?php if($country =="Fiji") echo 'selected'; ?>>Fiji</option>
							<option value="Finland" <?php if($country =="Finland") echo 'selected'; ?>>Finland</option>
							<option value="France" <?php if($country =="France") echo 'selected'; ?>>France</option>
							<option value="French Guiana" <?php if($country =="French Guiana") echo 'selected'; ?>>French Guiana</option>
							<option value="French Polynesia" <?php if($country =="French Polynesia") echo 'selected'; ?>>French Polynesia</option>
							<option value="French Southern Territories" <?php if($country =="French Southern Territories") echo 'selected'; ?>>French Southern Territories</option>
							<option value="Gabon" <?php if($country =="Gabon") echo 'selected'; ?>>Gabon</option>
							<option value="Gambia" <?php if($country =="Gambia") echo 'selected'; ?>>Gambia</option>
							<option value="Georgia" <?php if($country =="Georgia") echo 'selected'; ?>>Georgia</option>
							<option value="Germany" <?php if($country =="Germany") echo 'selected'; ?>>Germany</option>
							<option value="Ghana" <?php if($country =="Ghana") echo 'selected'; ?>>Ghana</option>
							<option value="Gibraltar" <?php if($country =="Gibraltar") echo 'selected'; ?>>Gibraltar</option>
							<option value="Greece" <?php if($country =="Greece") echo 'selected'; ?>>Greece</option>
							<option value="Greenland" <?php if($country =="Greenland") echo 'selected'; ?>>Greenland</option>
							<option value="Grenada" <?php if($country =="Grenada") echo 'selected'; ?>>Grenada</option>
							<option value="Guadeloupe" <?php if($country =="Guadeloupe") echo 'selected'; ?>>Guadeloupe</option>
							<option value="Guam" <?php if($country =="Guam") echo 'selected'; ?>>Guam</option>
							<option value="Guatemala" <?php if($country =="Guatemala") echo 'selected'; ?>>Guatemala</option>
							<option value="Guernsey" <?php if($country =="Guernsey") echo 'selected'; ?>>Guernsey</option>
							<option value="Guinea" <?php if($country =="Guinea") echo 'selected'; ?>>Guinea</option>
							<option value="Guinea-bissau" <?php if($country =="Guinea-bissau") echo 'selected'; ?>>Guinea-bissau</option>
							<option value="Guyana" <?php if($country =="Guyana") echo 'selected'; ?>>Guyana</option>
							<option value="Haiti" <?php if($country =="Haiti") echo 'selected'; ?>>Haiti</option>
							<option value="Heard Island and Mcdonald Islands" <?php if($country =="Heard Island and Mcdonald Islands") echo 'selected'; ?>>Heard Island and Mcdonald Islands</option>
							<option value="Holy See (Vatican City State)" <?php if($country =="Holy See (Vatican City State)") echo 'selected'; ?>>Holy See (Vatican City State)</option>
							<option value="Honduras" <?php if($country =="Honduras") echo 'selected'; ?>>Honduras</option>
							<option value="Hong Kong" <?php if($country =="Hong Kong") echo 'selected'; ?>>Hong Kong</option>
							<option value="Hungary" <?php if($country =="Hungary") echo 'selected'; ?>>Hungary</option>
							<option value="Iceland" <?php if($country =="Iceland") echo 'selected'; ?>>Iceland</option>
							<option value="India" dataterm="IN"<?php if($country =="India") echo 'selected'; ?>>India</option>
							<option value="Indonesia" <?php if($country =="Indonesia") echo 'selected'; ?>>Indonesia</option>
							<option value="Iran, Islamic Republic of" <?php if($country =="Iran, Islamic Republic of") echo 'selected'; ?>>Iran, Islamic Republic of</option>
							<option value="Iraq" <?php if($country =="Iraq") echo 'selected'; ?>>Iraq</option>
							<option value="Ireland" <?php if($country =="Ireland") echo 'selected'; ?>>Ireland</option>
							<option value="Isle of Man" <?php if($country =="Isle of Man") echo 'selected'; ?>>Isle of Man</option>
							<option value="Israel" <?php if($country =="Israel") echo 'selected'; ?>>Israel</option>
							<option value="Italy" <?php if($country =="Italy") echo 'selected'; ?>>Italy</option>
							<option value="Jamaica" <?php if($country =="Jamaica") echo 'selected'; ?>>Jamaica</option>
							<option value="Japan" <?php if($country =="Japan") echo 'selected'; ?>>Japan</option>
							<option value="Jersey" <?php if($country =="Jersey") echo 'selected'; ?>>Jersey</option>
							<option value="Jordan" <?php if($country =="Jordan") echo 'selected'; ?>>Jordan</option>
							<option value="Kazakhstan" <?php if($country =="Kazakhstan") echo 'selected'; ?>>Kazakhstan</option>
							<option value="Kenya" <?php if($country =="Kenya") echo 'selected'; ?>>Kenya</option>
							<option value="Kiribati" <?php if($country =="Kiribati") echo 'selected'; ?>>Kiribati</option>
							<option value="Korea, Democratic People's Republic of" <?php if($country =="Korea, Democratic People's Republic of") echo 'selected'; ?>>Korea, Democratic People’s Republic of</option>
							<option value="Korea, Republic of" <?php if($country =="Korea, Republic of") echo 'selected'; ?>>Korea, Republic of</option>
							<option value="Kuwait" <?php if($country =="Kuwait") echo 'selected'; ?>>Kuwait</option>
							<option value="Kyrgyzstan" <?php if($country =="Kyrgyzstan") echo 'selected'; ?>>Kyrgyzstan</option>
							<option value="Lao People's Democratic Republic" <?php if($country =="Lao People's Democratic Republic") echo 'selected'; ?>>Lao People’s Democratic Republic</option>
							<option value="Latvia" <?php if($country =="Latvia") echo 'selected'; ?>>Latvia</option>
							<option value="Lebanon" <?php if($country =="Lebanon") echo 'selected'; ?>>Lebanon</option>
							<option value="Lesotho" <?php if($country =="Lesotho") echo 'selected'; ?>>Lesotho</option>
							<option value="Liberia" <?php if($country =="Liberia") echo 'selected'; ?>>Liberia</option>
							<option value="Libyan Arab Jamahiriya" <?php if($country =="Libyan Arab Jamahiriya") echo 'selected'; ?>>Libyan Arab Jamahiriya</option>
							<option value="Liechtenstein" <?php if($country =="Liechtenstein") echo 'selected'; ?>>Liechtenstein</option>
							<option value="Lithuania" <?php if($country =="Lithuania") echo 'selected'; ?>>Lithuania</option>
							<option value="Luxembourg" <?php if($country =="Luxembourg") echo 'selected'; ?>>Luxembourg</option>
							<option value="Macao" <?php if($country =="Macao") echo 'selected'; ?>>Macao</option>
							<option value="Macedonia, The Former Yugoslav Republic of" <?php if($country =="Macedonia, The Former Yugoslav Republic of") echo 'selected'; ?>>Macedonia, The Former Yugoslav Republic of</option>
							<option value="Madagascar" <?php if($country =="Madagascar") echo 'selected'; ?>>Madagascar</option>
							<option value="Malawi" <?php if($country =="Malawi") echo 'selected'; ?>>Malawi</option>
							<option value="Malaysia" <?php if($country =="Malaysia") echo 'selected'; ?>>Malaysia</option>
							<option value="Maldives" <?php if($country =="Maldives") echo 'selected'; ?>>Maldives</option>
							<option value="Mali" <?php if($country =="Mali") echo 'selected'; ?>>Mali</option>
							<option value="Malta" <?php if($country =="Malta") echo 'selected'; ?>>Malta</option>
							<option value="Marshall Islands" <?php if($country =="Marshall Islands") echo 'selected'; ?>>Marshall Islands</option>
							<option value="Martinique" <?php if($country =="Martinique") echo 'selected'; ?>>Martinique</option>
							<option value="Mauritania" <?php if($country =="Mauritania") echo 'selected'; ?>>Mauritania</option>
							<option value="Mauritius" <?php if($country =="Mauritius") echo 'selected'; ?>>Mauritius</option>
							<option value="Mayotte" <?php if($country =="Mayotte") echo 'selected'; ?>>Mayotte</option>
							<option value="Mexico" <?php if($country =="Mexico") echo 'selected'; ?>>Mexico</option>
							<option value="Micronesia, Federated States of" <?php if($country =="Micronesia, Federated States of") echo 'selected'; ?>>Micronesia, Federated States of</option>
							<option value="Moldova, Republic of" <?php if($country =="Moldova, Republic of") echo 'selected'; ?>>Moldova, Republic of</option>
							<option value="Monaco" <?php if($country =="Monaco") echo 'selected'; ?>>Monaco</option>
							<option value="Mongolia" <?php if($country =="Mongolia") echo 'selected'; ?>>Mongolia</option>
							<option value="Montenegro" <?php if($country =="Montenegro") echo 'selected'; ?>>Montenegro</option>
							<option value="Montserrat" <?php if($country =="Montserrat") echo 'selected'; ?>>Montserrat</option>
							<option value="Morocco" <?php if($country =="Morocco") echo 'selected'; ?>>Morocco</option>
							<option value="Mozambique" <?php if($country =="Mozambique") echo 'selected'; ?>>Mozambique</option>
							<option value="Myanmar" <?php if($country =="Myanmar") echo 'selected'; ?>>Myanmar</option>
							<option value="Namibia" <?php if($country =="Namibia") echo 'selected'; ?>>Namibia</option>
							<option value="Nauru" <?php if($country =="Nauru") echo 'selected'; ?>>Nauru</option>
							<option value="Nepal" <?php if($country =="Nepal") echo 'selected'; ?>>Nepal</option>
							<option value="Netherlands" <?php if($country =="Netherlands") echo 'selected'; ?>>Netherlands</option>
							<option value="Netherlands Antilles" <?php if($country =="Netherlands Antilles") echo 'selected'; ?>>Netherlands Antilles</option>
							<option value="New Caledonia" <?php if($country =="New Caledonia") echo 'selected'; ?>>New Caledonia</option>
							<option value="New Zealand" <?php if($country =="New Zealand") echo 'selected'; ?>>New Zealand</option>
							<option value="Nicaragua" <?php if($country =="Nicaragua") echo 'selected'; ?>>Nicaragua</option>
							<option value="Niger" <?php if($country =="Niger") echo 'selected'; ?>>Niger</option>
							<option value="Nigeria" <?php if($country =="Nigeria") echo 'selected'; ?>>Nigeria</option>
							<option value="Niue" <?php if($country =="Niue") echo 'selected'; ?>>Niue</option>
							<option value="Norfolk Island" <?php if($country =="Norfolk Island") echo 'selected'; ?>>Norfolk Island</option>
							<option value="Northern Mariana Islands" <?php if($country =="Northern Mariana Islands") echo 'selected'; ?>>Northern Mariana Islands</option>
							<option value="Norway" <?php if($country =="Norway") echo 'selected'; ?>>Norway</option>
							<option value="Oman" <?php if($country =="Oman") echo 'selected'; ?>>Oman</option>
							<option value="Pakistan" <?php if($country =="Pakistan") echo 'selected'; ?>>Pakistan</option>
							<option value="Palau" <?php if($country =="Palau") echo 'selected'; ?>>Palau</option>
							<option value="Palestinian Territory, Occupied" <?php if($country =="Palestinian Territory, Occupied") echo 'selected'; ?>>Palestinian Territory, Occupied</option>
							<option value="Panama" <?php if($country =="Panama") echo 'selected'; ?>>Panama</option>
							<option value="Papua New Guinea" <?php if($country =="Papua New Guinea") echo 'selected'; ?>>Papua New Guinea</option>
							<option value="Paraguay" <?php if($country =="Paraguay") echo 'selected'; ?>>Paraguay</option>
							<option value="Peru" <?php if($country =="Peru") echo 'selected'; ?>>Peru</option>
							<option value="Philippines" <?php if($country =="Philippines") echo 'selected'; ?>>Philippines</option>
							<option value="Pitcairn" <?php if($country =="Pitcairn") echo 'selected'; ?>>Pitcairn</option>
							<option value="Poland" <?php if($country =="Poland") echo 'selected'; ?>>Poland</option>
							<option value="Portugal" <?php if($country =="Portugal") echo 'selected'; ?>>Portugal</option>
							<option value="Puerto Rico" <?php if($country =="Puerto Rico") echo 'selected'; ?>>Puerto Rico</option>
							<option value="Qatar" <?php if($country =="Qatar") echo 'selected'; ?>>Qatar</option>
							<option value="Reunion" <?php if($country =="Reunion") echo 'selected'; ?>>Reunion</option>
							<option value="Romania" <?php if($country =="Romania") echo 'selected'; ?>>Romania</option>
							<option value="Russian Federation" <?php if($country =="Russian Federation") echo 'selected'; ?>>Russian Federation</option>
							<option value="Rwanda" <?php if($country =="Rwanda") echo 'selected'; ?>>Rwanda</option>
							<option value="Saint Helena" <?php if($country =="Saint Helena") echo 'selected'; ?>>Saint Helena</option>
							<option value="Saint Kitts and Nevis" <?php if($country =="Saint Kitts and Nevis") echo 'selected'; ?>>Saint Kitts and Nevis</option>
							<option value="Saint Lucia" <?php if($country =="Saint Lucia") echo 'selected'; ?>>Saint Lucia</option>
							<option value="Saint Pierre and Miquelon" <?php if($country =="Saint Pierre and Miquelon") echo 'selected'; ?>>Saint Pierre and Miquelon</option>
							<option value="Saint Vincent and The Grenadines" <?php if($country =="Saint Vincent and The Grenadines") echo 'selected'; ?>>Saint Vincent and The Grenadines</option>
							<option value="Samoa" <?php if($country =="Samoa") echo 'selected'; ?>>Samoa</option>
							<option value="San Marino" <?php if($country =="San Marino") echo 'selected'; ?>>San Marino</option>
							<option value="Sao Tome and Principe" <?php if($country =="Sao Tome and Principe") echo 'selected'; ?>>Sao Tome and Principe</option>
							<option value="Saudi Arabia" <?php if($country =="Saudi Arabia") echo 'selected'; ?>>Saudi Arabia</option>
							<option value="Senegal" <?php if($country =="Senegal") echo 'selected'; ?>>Senegal</option>
							<option value="Serbia" <?php if($country =="Serbia") echo 'selected'; ?>>Serbia</option>
							<option value="Seychelles" <?php if($country =="Seychelles") echo 'selected'; ?>>Seychelles</option>
							<option value="Sierra Leone" <?php if($country =="Sierra Leone") echo 'selected'; ?>>Sierra Leone</option>
							<option value="Singapore" <?php if($country =="Singapore") echo 'selected'; ?>>Singapore</option>
							<option value="Slovakia" <?php if($country =="Slovakia") echo 'selected'; ?>>Slovakia</option>
							<option value="Slovenia" <?php if($country =="Slovenia") echo 'selected'; ?>>Slovenia</option>
							<option value="Solomon Islands" <?php if($country =="Solomon Islands") echo 'selected'; ?>>Solomon Islands</option>
							<option value="Somalia" <?php if($country =="Somalia") echo 'selected'; ?>>Somalia</option>
							<option value="South Africa" <?php if($country =="South Africa") echo 'selected'; ?>>South Africa</option>
							<option value="South Georgia and The South Sandwich Islands" <?php if($country =="South Georgia and The South Sandwich Islands") echo 'selected'; ?>>South Georgia and The South Sandwich Islands</option>
							<option value="Spain" <?php if($country =="Spain") echo 'selected'; ?>>Spain</option>
							<option value="Sri Lanka" <?php if($country =="Sri Lanka") echo 'selected'; ?>>Sri Lanka</option>
							<option value="Sudan" <?php if($country =="Sudan") echo 'selected'; ?>>Sudan</option>
							<option value="Suriname" <?php if($country =="Suriname") echo 'selected'; ?>>Suriname</option>
							<option value="Svalbard and Jan Mayen" <?php if($country =="Svalbard and Jan Mayen") echo 'selected'; ?>>Svalbard and Jan Mayen</option>
							<option value="Swaziland" <?php if($country =="Swaziland") echo 'selected'; ?>>Swaziland</option>
							<option value="Sweden" <?php if($country =="Sweden") echo 'selected'; ?>>Sweden</option>
							<option value="Switzerland" <?php if($country =="Switzerland") echo 'selected'; ?>>Switzerland</option>
							<option value="Syrian Arab Republic" <?php if($country =="Syrian Arab Republic") echo 'selected'; ?>>Syrian Arab Republic</option>
							<option value="Taiwan" <?php if($country =="Taiwan") echo 'selected'; ?>>Taiwan</option>
							<option value="Tajikistan" <?php if($country =="Tajikistan") echo 'selected'; ?>>Tajikistan</option>
							<option value="Tanzania, United Republic of" <?php if($country =="Tanzania, United Republic of") echo 'selected'; ?>>Tanzania, United Republic of</option>
							<option value="Thailand" <?php if($country =="Thailand") echo 'selected'; ?>>Thailand</option>
							<option value="Timor-leste" <?php if($country =="Timor-leste") echo 'selected'; ?>>Timor-leste</option>
							<option value="Togo" <?php if($country =="Togo") echo 'selected'; ?>>Togo</option>
							<option value="Tokelau" <?php if($country =="Tokelau") echo 'selected'; ?>>Tokelau</option>
							<option value="Tonga" <?php if($country =="Tonga") echo 'selected'; ?>>Tonga</option>
							<option value="Trinidad and Tobago" <?php if($country =="Trinidad and Tobago") echo 'selected'; ?>>Trinidad and Tobago</option>
							<option value="Tunisia" <?php if($country =="Tunisia") echo 'selected'; ?>>Tunisia</option>
							<option value="Turkey" <?php if($country =="Turkey") echo 'selected'; ?>>Turkey</option>
							<option value="Turkmenistan" <?php if($country =="Turkmenistan") echo 'selected'; ?>>Turkmenistan</option>
							<option value="Turks and Caicos Islands" <?php if($country =="Turks and Caicos Islands") echo 'selected'; ?>>Turks and Caicos Islands</option>
							<option value="Tuvalu" <?php if($country =="Tuvalu") echo 'selected'; ?>>Tuvalu</option>
							<option value="Uganda" <?php if($country =="Uganda") echo 'selected'; ?>>Uganda</option>
							<option value="Ukraine" <?php if($country =="Ukraine") echo 'selected'; ?>>Ukraine</option>
							<option value="United Arab Emirates" <?php if($country =="United Arab Emirates") echo 'selected'; ?>>United Arab Emirates</option>
							<option value="United Kingdom" <?php if($country =="United Kingdom") echo 'selected'; ?>>United Kingdom</option>
							<option value="United States" <?php if($country =="United States") echo 'selected'; ?>>United States</option>
							<option value="United States Minor Outlying Islands" <?php if($country =="United States Minor Outlying Islands") echo 'selected'; ?>>United States Minor Outlying Islands</option>
							<option value="Uruguay" <?php if($country =="Uruguay") echo 'selected'; ?>>Uruguay</option>
							<option value="Uzbekistan" <?php if($country =="Uzbekistan") echo 'selected'; ?>>Uzbekistan</option>
							<option value="Vanuatu" <?php if($country =="Vanuatu") echo 'selected'; ?>>Vanuatu</option>
							<option value="Venezuela" <?php if($country =="Venezuela") echo 'selected'; ?>>Venezuela</option>
							<option value="Viet Nam" <?php if($country =="Viet Nam") echo 'selected'; ?>>Viet Nam</option>
							<option value="Virgin Islands, British" <?php if($country =="Virgin Islands, British") echo 'selected'; ?>>Virgin Islands, British</option>
							<option value="Virgin Islands, U.S." <?php if($country =="Virgin Islands, U.S.") echo 'selected'; ?>>Virgin Islands, U.S.</option>
							<option value="Wallis and Futuna" <?php if($country =="Wallis and Futuna") echo 'selected'; ?>>Wallis and Futuna</option>
							<option value="Western Sahara" <?php if($country =="Western Sahara") echo 'selected'; ?>>Western Sahara</option>
							<option value="Yemen" <?php if($country =="Yemen") echo 'selected'; ?>>Yemen</option>
							<option value="Zambia" <?php if($country =="Zambia") echo 'selected'; ?>>Zambia</option>
							<option value="Zimbabwe" <?php if($country =="Zimbabwe") echo 'selected'; ?>>Zimbabwe</option>
						</select>
					</div>
					<div class="py-2 ml-3 citycol">
						<h6 class="font-weight-bold">City</h6>
						<input id="City" list="citylist" class="ct-textInputField citytextfield" name="city" tabindex="7" maxlength="250" type="text" autocomplete="off" value="<?php echo $city; ?>" placeholder="Select a city…">
						<datalist id="citylist"></datalist>
					</div> 
					<!-- <div style="display: none; position: absolute; left: 638px; top: 818px;" id="City-ExtensionsId" class="em-suggestion_list"><ul><li><div>Mathura</div></li><li class=""><div>Mathana</div></li></ul></div> -->
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold">Trial Status</h6>
							<div class="form-group"> <input type="checkbox" class="status" value="Recruiting,Available" name="status[]" <?php if(in_array("Recruiting,Available", $status)) echo 'checked'; ?>> <label for="lorem">Recruiting now</label> </div>
							<div class="form-group"> <input type="checkbox" class="status" value="Not Yet Recruiting,Active_not_recruiting" name="status[]" <?php if(in_array("Not Yet Recruiting,Active_not_recruiting", $status)) echo 'checked'; ?>> <label for="lorem">Not currently recruiting</label> </div>
							<!-- <div class="form-group"> <input type="checkbox" class="status" value="Not Yet Recruiting" name="status[]" <?php //if(in_array("Not Yet Recruiting", $status)) echo 'checked'; ?>> <label for="lorem">Not Yet Recruiting</label> </div> -->
							<div class="form-group"> <input type="checkbox" class="status" value="Completed,Terminated,Suspended,Withdrawn" name="status[]" <?php if(in_array("Completed,Terminated,Suspended,Withdrawn", $status)) echo 'checked'; ?>> <label for="lorem">Finished trials</label> </div>
							<!-- <div class="form-group"> <input type="checkbox" class="status" value="Terminated" name="status[]" <?php //if(in_array("Terminated", $status)) echo 'checked'; ?>> <label for="lorem">Terminated</label> </div>
							<div class="form-group"> <input type="checkbox" class="status" value="Suspended" name="status[]" <?php //if(in_array("Suspended", $status)) echo 'checked'; ?>> <label for="lorem">Suspended</label> </div>
							<div class="form-group"> <input type="checkbox" class="status" value="Withdrawn" name="status[]" <?php //if(in_array("Withdrawn", $status)) echo 'checked'; ?>> <label for="lorem">Withdrawn</label> </div> -->
							<!-- <div class="form-group"> <input type="checkbox" class="status" value="Unknown status" name="status[]" <?php //if(in_array("Unknown status", $status)) echo 'checked'; ?>> <label for="lorem">Unknown</label> </div> -->
							<!-- <div class="form-group"> <input type="checkbox" class="status" value="Enrolling by Invitation" name="status[]" <?php //if(in_array("Enrolling by Invitation", $status)) echo 'checked'; ?>> <label for="lorem">Enrolling by Invitation</label> </div> -->
					</div>
					<!-- <div class="py-2 ml-3">
						<h6 class="font-weight-bold">Sort</h6> 
							<div class="form-group"> <input type="radio" class="sort" name="sort" value="DESC" <?php //if($sort=='DESC') echo 'checked'; ?>> <label for="DESC">Latest Trials</label> </div>
							<div class="form-group"> <input type="radio" class="sort" name="sort" value="ASC" <?php //if($sort=='ASC') echo 'checked'; ?>> <label for="ASC">Oldest Trials</label> </div>
					</div> -->
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold">I am interested in</h6>
							<div class="form-group"> <input type="checkbox" class="type" name="type[]" value="Interventional,Expanded Access"<?php if(in_array("Interventional,Expanded Access", $type)) echo 'checked'; ?>> <label for="Interventional"><span class="customToolLink">New treatments<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">Trials that involve a new treatment.</span></span></span></label> </div>
							<!-- <div class="form-group"> <input type="checkbox" class="type" name="type[]" value="Expanded Access"<?php //if(in_array("Expanded Access", $type)) echo 'checked'; ?>> <label for="Expanded Access">Expanded Access</label> </div> -->
							<div class="form-group"> <input type="checkbox" class="type" name="type[]" value="Observational"<?php if(in_array("Observational", $type)) echo 'checked'; ?>> <label for="Observational"><span class="customToolLink">Other trials<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">Trials that contribute to research but do not actively involve having a new treatment.</span></span></span></label> </div>
					</div>
					<!-- <div class="py-2 ml-3">
						<h6 class="font-weight-bold">Study Results</h6>
						<form>
							<div class="form-group"> <input type="checkbox" id="lorem"> <label for="lorem">Lorem Ipsum</label> </div>
						</form>
					</div> -->
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold"><span class="customToolLink">Trial Phase<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">The stages of clinical trial research.</span></span></span></h6>
							<div class="form-group"> <input type="checkbox" class="phase" name="phase[]" value="Phase 1" <?php if(in_array("Phase 1", $phase)) echo 'checked'; ?>> <label for="Phase 1"><span class="customToolLink">Phase 1<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">Assesses the safety and dose of a drug/treatment. Patients may still benefit from its effects.</span></span></span></label> </div>
							<div class="form-group"> <input type="checkbox" class="phase" name="phase[]" value="Phase 2" <?php if(in_array("Phase 2", $phase)) echo 'checked'; ?>> <label for="Phase 2"><span class="customToolLink">Phase 2<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">Assesses the effectiveness of a drug/ treatment.</span></span></span></label> </div>
							<div class="form-group"> <input type="checkbox" class="phase" name="phase[]" value="Phase 3" <?php if(in_array("Phase 3", $phase)) echo 'checked'; ?>> <label for="Phase 3"><span class="customToolLink">Phase 3<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">Assesses the effectiveness of a drug/ treatment but on a larger scale.</span></span></span></label> </div>
							<div class="form-group"> <input type="checkbox" class="phase" name="phase[]" value="Phase 4" <?php if(in_array("Phase 4", $phase)) echo 'checked'; ?>> <label for="Phase 4"><span class="customToolLink">Phase 4<span class="hidden glossary-tooltip-content clearfix" original_left="545.484375" style="transform: translateZ(0px);"><span class="glossary-tooltip-text">Tests the long-term effects of licenced drugs/ treatments and how best to optimise them.</span></span></span></label> </div>
					</div>
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold">Clinicaltrial.gov ID/ NCT Number</h6>
						<div class="form-group">
							<input type="text" class="trial_id" name="trial_id" value="<?php echo $trial_id; ?>" placeholder="e.g. NCT04132895">
						</div>
					</div>
					<div class="py-2 ml-3">
						<h6 class="font-weight-bold">Keyword </h6>
						<div class="form-group">
							<input name="term" type="text" placeholder="e.g. drug name" value="<?php echo $term; ?>">
						</div>
					</div>
					 
				</form>
			</section>
		</div>
		<div class="col-md-9 data_study_list"> 
			<div class=" result_print details_download_btn_div">
				<button class="detail_download_button" onclick="printResult();"><span title="Download as PDF">Download your results <img src="/wp-content/uploads/2022/06/download_icon.png"></span></button>
			</div>
			<?php if(!empty($arrress->result)){ ?> 
				<div class="table-responsive" id="resTable">
					<table class="table table-striped">
					  <thead>
						<tr>
							<th scope="col">Trial Name</th>
							<th scope="col">Status</th>
							<th scope="col">Phase</th>
							<th scope="col">Country </th>
							<th scope="col">City</th>
						</tr> 
					  </thead>
					  
					  <tbody> 
						  <?php 
								$resreq = "No";
							if (in_array("Terminated", $status)){
								$resreq = "Yes";
							}
							$hemcont = 1;
						  $c=1; foreach($arrress->result as $study_field){ //echo "<pre>"; print_r($study_field); echo "</pre>"; 
							//if($c<=10){
								
							$echostatus = $study_field->OverallStatus;
							$echophase = $study_field->Phase;
							$echolocationcountry = $study_field->LocationCountry;
							$echolocationcity = $study_field->LocationCity;
							
							if($study_field->CustomOverallStatus != "")
								$echostatus = $study_field->CustomOverallStatus;
							if($study_field->CustomPhase != "")
								$echophase = $study_field->CustomPhase;
							if($study_field->CustomLocationCountry != "")
								$echolocationcountry = $study_field->CustomLocationCountry;
							if($study_field->CustomLocationCity != "")
								$echolocationcity = $study_field->CustomLocationCity;
							// print_r($status);
							// echo $resreq;
							// echo $echostatus;
							// if(!empty($status) && $resreq == "No" && $echostatus == "Terminated"){
								
							// }else{
							$hemcont++;
						  ?>
							<tr>
								<th scope="row"><a href="/single-study?id=<?php echo $study_field->NCTId; ?>" class="singlelink"><?php echo $study_field->BriefTitle; ?></a><p class="resbreiftrial"><?php if($study_field->CustomBriefSummary != "" || $study_field->BriefSummary != ""){ ?>
								<?php if($study_field->CustomBriefSummary == "" ){ echo substr($study_field->BriefSummary, 0, 200); if(strlen($study_field->BriefSummary) > 200){ echo '...'; } } else{ echo substr($study_field->CustomBriefSummary, 0, 200); if(strlen($study_field->CustomBriefSummary) > 200){ echo '...'; } } ?>
								<?php }else{ echo "-"; } ?><?php //echo substr($study_field->BriefSummary, 0, 100); ?></p></th>
								<td><?php echo implode(", ",array_unique(explode(',', $echostatus))); //if(implode(", ",array_unique(explode(',', $echostatus))) == 'Recruiting' || implode(", ",array_unique(explode(',', $echostatus))) == 'Available') echo 'Recruiting now'; elseif((implode(", ",array_unique(explode(',', $echostatus))) == 'Active, not recruiting') || (implode(", ",array_unique(explode(',', $echostatus))) == 'Not yet Recruiting')) echo 'Not currently recruiting'; elseif((implode(", ",array_unique(explode(',', $echostatus))) == 'Completed') || (implode(", ",array_unique(explode(',', $echostatus))) == 'Terminated') || (implode(", ",array_unique(explode(',', $echostatus))) == 'Suspended') || (implode(", ",array_unique(explode(',', $echostatus))) == 'Withdrawn')) echo 'Finished trials'; else echo implode(", ",array_unique(explode(',', $echostatus))); ?></td>
								<td><?php echo implode(", ",array_unique(explode(',', $echophase))); ?></td>
								<td><?php echo substr(implode(", ",array_unique(explode(',', $echolocationcountry))), 0, 200); if (strlen(implode(", ",array_unique(explode(',', $echolocationcountry)))) > 200) echo "..."; ?></td>
								<td><?php echo substr(implode(", ",array_unique(explode(',', $echolocationcity))), 0, 200); if (strlen(implode(", ",array_unique(explode(',', $echolocationcity)))) > 200) echo "...";?></td>
							</tr>
							<?php //}
							$c++; } //} ?> 
					  </tbody>
					  
					</table>
				</div>
				<div class="mobile_result">	
					<ul class="mobile_result_ul">
					<?php $c=1; foreach($arrress->result as $study_field){
						$echostatus = $study_field->OverallStatus;
						$echophase = $study_field->Phase;
						$echolocationcountry = $study_field->LocationCountry;
						$echolocationcity = $study_field->LocationCity;
						
						if($study_field->CustomOverallStatus != "")
							$echostatus = $study_field->CustomOverallStatus;
						if($study_field->CustomPhase != "")
							$echophase = $study_field->CustomPhase;
						if($study_field->CustomLocationCountry != "")
							$echolocationcountry = $study_field->CustomLocationCountry;
						if($study_field->CustomLocationCity != "")
							$echolocationcity = $study_field->CustomLocationCity;
						$hemcont++; ?>
						<li>
							<div class="mobile_result_div">
								<p class="mobile_result_heading">Trial Name:</p>
								<a href="/single-study?id=<?php echo $study_field->NCTId; ?>" class="singlelink"><?php echo $study_field->BriefTitle; ?></a>
								<p class="resbreiftrial"><?php if($study_field->CustomBriefSummary != "" || $study_field->BriefSummary != ""){ ?><?php if($study_field->CustomBriefSummary == "" ){ echo substr($study_field->BriefSummary, 0, 200); if(strlen($study_field->BriefSummary) > 200){ echo '...'; } } else{ echo substr($study_field->CustomBriefSummary, 0, 200); if(strlen($study_field->CustomBriefSummary) > 200){ echo '...'; } } ?><?php }else{ echo "-"; } ?></p>
							</div>
							<div class="mobile_result_div">
								<p class="mobile_result_heading">Status:</p>
								<p><?php echo implode(", ",array_unique(explode(',', $echostatus))); ?></p>
							</div>
							<div class="mobile_result_div">
								<p class="mobile_result_heading">Phase:</p>
								<p><?php echo implode(", ",array_unique(explode(',', $echophase))); ?></p>
							</div class="mobile_result_div">
							<div class="mobile_result_div">
								<p class="mobile_result_heading">Country:</p>
								<p><?php echo substr(implode(", ",array_unique(explode(',', $echolocationcountry))), 0, 200); if (strlen(implode(", ",array_unique(explode(',', $echolocationcountry)))) > 200) echo "..."; ?></p>
							</div>
							<div class="mobile_result_div">
								<p class="mobile_result_heading">City:</p>
								<p><?php echo substr(implode(", ",array_unique(explode(',', $echolocationcity))), 0, 200); if (strlen(implode(", ",array_unique(explode(',', $echolocationcity)))) > 200) echo "...";?></p>
							</div>
						</li>
						<?php $c++; } ?> 
					</ul>
				</div>
			<?php }else{ ?>
				<h2>No results found:</h2>
				<p class="not_p">Return to the clinical trial <a href="/clinical-trials">search engine</a> and widen your search.</p>
				<p class="not_p">Visit our <a href="/cant-find-a-clinical-trial/">Can’t Find a Trial</a> page for alternative options including expanded access programmes and nonspecific early phase trials.</p>
			<?php }
				if($hemcont == 1){ ?>
					<h2>No results found:</h2>
				<p class="not_p">Return to the clinical trial <a href="/clinical-trials">search engine</a> and widen your search.</p>
				<p class="not_p">Visit our <a href="/cant-find-a-clinical-trial/">Can’t Find a Trial</a> page for alternative options including expanded access programmes and nonspecific early phase trials.</p>
				<?php }
			?>
		</div>
		<?php 
			$MinRank = $page_no * 10;
			// $MinRank = $arrres->StudyFieldsResponse->MinRank;
			// $MaxRank = $arrres->StudyFieldsResponse->MaxRank;
			// $total_records = count($arrress->result);
			$total_records = $arrress->count;
			$return_records = 10; 
			$total_pages = ceil($total_records/10);
			$current_page = $MinRank/10;
		?>
		<?php if($total_pages > 1){ ?>
			<div class="center">
				<div class="pagination">
					<?php if($current_page>1){ ?><a href="<?php echo esc_url( add_query_arg( 'page_no', $current_page-1 ) ); ?>">&laquo;</a><?php } ?>
					<?php for($i=1; $i<=$total_pages; $i++ ){ ?>
						<?php if(($i<3 || $i>$total_pages-2) || ($i>$current_page-2 && $i<$current_page+2)){ ?> 
							<a <?php if($current_page == $i){ ?>class="active"<?php }else{ ?> href='<?php echo esc_url( add_query_arg( 'page_no', $i ) ); ?>'<?php } ?>><?php echo $i; ?></a>
						<?php } else{
								if($i==$current_page-2) echo '<span class="dot_dot">. . </span>'; 
								if($i==$current_page+2) echo '<span class="dot_dot">. . </span>'; 
							}
						} ?>
					<?php if($current_page<$total_pages){ ?><a href="<?php echo esc_url( add_query_arg( 'page_no', $current_page+1 ) ); ?>">&raquo;</a><?php } ?>
				</div>
			</div>
		<?php } ?>
	</div>
	<div class="row mt-4">
		<div class="col-12">
			<div class="detail_summry_div">
				<h3 id="detail_summry_h3">Disclaimer</h3>
				<ul>
					<li class="desclaimer_text">ONTEX is intended to supplement, not replace, your healthcare team. Patients should always discuss a clinical trial with their healthcare team.  If a patient is eligible for a trial the trial team will be able to provide more in-depth information about the trial so the patient can make an informed decision before taking part.
Trial information has been sourced from <a href="http://www.clinicaltrials.gov">www.clinicaltrials.gov</a>. The content is then reviewed weekly by the Osteosarcoma Now team. All the trials also have a patient-friendly summary and key information section written by the team at Osteosarcoma Now. We have also included a description of the medications being used in the trial and summarised the inclusion and exclusion criteria in the ‘who is this trial (not) for’ sections.
To the best of our knowledge the clinical trial database is up-to-date and accurate.However, we cannot assume any liability for the accuracy or completeness of the information.</li> 
				</ul>
			</div>
		</div>
	</div>
</div>

<?php get_footer(); ?>
