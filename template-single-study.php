<?php /* Template Name: Single Study */ get_header(); $page_id = get_the_id();

// Prefer $_GET for templates, and unslash/sanitize in WordPress context.
$req = $_GET;
if (function_exists('wp_unslash')) {
	$req = wp_unslash($req);
}

$search_query = 'Osteosarcoma';
$nctid = '';
if (isset($req['id']) && $req['id'] !== '') {
	$nctid = function_exists('sanitize_text_field') ? sanitize_text_field($req['id']) : (string) $req['id'];
	// $search_query .= " AND AREA[NCTId]$nctid";
	$search_query = "AREA[NCTId]$nctid";
}

if ($nctid === '') {
	echo '<div class="container"><p>' . esc_html__('Missing study id.', 'ontex') . '</p></div>';
	get_footer();
	return;
}
$urll = str_replace(" ","+","http://jayr57.sg-host.com/api/get-trail?trail_id=$nctid");
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
$customresult=$arrress->result[0];
// echo "<pre>";print_r($arrress->result[0]);echo "</pre>"; 

$url = str_replace(" ","+","https://clinicaltrials.gov/api/query/study_fields?expr=$search_query&fields=LocationCountry,LocationCity,LocationContactEMail,LocationContactName,LocationContactPhone,LocationContactPhoneExt,LocationContactRole,LocationFacility,LocationState,LocationStatus,LocationZip,StudyType,Phase,OverallStatus,MinimumAge,MaximumAge,CentralContactName,CentralContactPhone,CentralContactEMail,NCTId&fmt=JSON");
//echo str_replace(" ","+","https://clinicaltrials.gov/api/query/full_studies?expr=$search_query&fmt=json");
//echo $url;
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
$study_field = $arrres->StudyFieldsResponse->StudyFields[0];
//echo "<pre>";print_r($study_field);echo "</pre>";

$url2 = str_replace(" ","+","https://clinicaltrials.gov/api/query/study_fields?expr=$search_query&fields=BriefSummary,Condition,BriefTitle,ArmGroupInterventionName,InterventionDescription,InterventionOtherName,EligibilityCriteria,LastUpdatePostDate&fmt=JSON");
//$url = str_replace(" ","+","https://clinicaltrials.gov/api/query/full_studies?expr=$search_query&fmt=json");
//echo $url2;
$curl2 = curl_init();
curl_setopt_array($curl2, array(
  CURLOPT_URL => $url2,
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_TIMEOUT => 30,
  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
  CURLOPT_CUSTOMREQUEST => "GET",
  CURLOPT_HTTPHEADER => array(
    "cache-control: no-cache"
  ),
));
$response2 = curl_exec($curl2);
$err2 = curl_error($curl2);
curl_close($curl2); 
$arrres2 = json_decode($response2);
$study_field2 = $arrres2->StudyFieldsResponse->StudyFields[0];
//echo "<pre>";print_r($study_field2);echo "</pre>";

function get_string_between($string, $start, $end){
    $string = ' ' . $string;
    $ini = strpos($string, $start);
    if ($ini == 0) return '';
    $ini += strlen($start);
    $len = strpos($string, $end, $ini) - $ini;
    return substr($string, $ini, $len);
} 
if($customresult->CustomEligibilityCriteria != "" ) $customresult->EligibilityCriteria = $customresult->CustomEligibilityCriteria;
	
$eligibility = isset($customresult->EligibilityCriteria) ? (string) $customresult->EligibilityCriteria : '';
$parsedInclusionCriteria = array_filter(array_unique(explode("\n", get_string_between($eligibility, 'Inclusion Criteria:', 'Exclusion Criteria'))));
$parsedExclusionCriteria = [];
if (strpos($eligibility, 'Exclusion Criteria:') !== false) {
	$parts = explode('Exclusion Criteria:', $eligibility, 2);
	$parsedExclusionCriteria = array_filter(array_unique(explode("\n", $parts[1] ?? '')));
}
if(empty($parsedInclusionCriteria)){
	$parsedInclusionCriteria = array_filter(array_unique(explode("\n", get_string_between($eligibility, 'INCLUSION CRITERIA', 'EXCLUSION CRITERIA'))));
}
if(empty($parsedExclusionCriteria) && strpos($eligibility, 'EXCLUSION CRITERIA') !== false){
	$parts = explode('EXCLUSION CRITERIA', $eligibility, 2);
	$parsedExclusionCriteria = array_filter(array_unique(explode("\n", $parts[1] ?? '')));
}
// $study_field = $study_field2 = $customresult;
?>
	<div class="container full_mobile">
	<div class="single_study_data" id="single_study_data">
		<div class="row">
			<div class="col-12"> 
				<h1><?php if($customresult->CustomBriefTitle == "" ) echo $customresult->BriefTitle; else echo $customresult->CustomBriefTitle; ?></h1>
				<p class="last_posted_date"><b>Last Update Posted :</b> <?php getCustomData('LastUpdatePostDate', 'CustomLastUpdatePostDate', $customresult); ?></p>
			</div>
			<div class="col-12">
				<div class="detail_summry_div">
					<h3 id="detail_summry_h3">The aim of the trial </h3>
					<?php if($customresult->CustomBriefSummary != "" || $customresult->BriefSummary != ""){ ?>
					<ul>
						<li><?php if($customresult->CustomBriefSummary == "" ) echo $customresult->BriefSummary; else echo $customresult->CustomBriefSummary; ?></li>
					</ul>
					<?php }else{ echo "-"; } ?>
				</div>
			</div>
		</div>
		<div class="row">
			<div class="col-12">
			<div class="details_download_btn_div">
				<button class="detail_download_button" onclick='printReceipt();'><span title="Download as PDF">Download your results <img src="/wp-content/uploads/2022/06/download_icon.png" /></span></button>
			</div>
				<div class="key_point_detail">
					<dl class="key_point_list" id="key_facts">
						<div class="key_point_list_div">
							<dt>Country</dt>
							<dd><?php getCustomData('LocationCountry', 'CustomLocationCountry', $customresult); ?></dd>
							<!-- <dd><?php //if(empty($study_field->LocationCountry)) echo "-"; $i=0; foreach(array_unique($study_field->LocationCountry) as $location_country){ if($i>0)echo ", "; echo $location_country; $i++;}?></dd> -->
						</div>
						<div class="key_point_list_div">
							<dt>Locations</dt>
							<dd><?php getCustomData('LocationCity', 'CustomLocationCity', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Trial Type</dt>
							<dd><?php getCustomData('StudyType', 'CustomStudyType', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Trial Phase</dt>
							<dd><?php getCustomData('Phase', 'CustomPhase', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Trial Status</dt>
							<dd><?php getCustomData('OverallStatus', 'CustomOverallStatus', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Minimum age</dt>
							<dd><?php getCustomData('MinimumAge', 'CustomMinimumAge', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Maximum age</dt>
							<dd><?php getCustomData('MaximumAge', 'CustomMaximumAge', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Key Contact</dt>
							<dd><?php if(empty($study_field->CentralContactName) && empty($study_field->CentralContactPhone) && empty($study_field->CentralContactEMail)) echo "-"; 
							getCustomData('CentralContactName', 'CustomCentralContactName', $customresult);
							getCustomData('CentralContactPhone', 'CustomCentralContactPhone', $customresult);
							getCustomData('CentralContactEMail', 'CustomCentralContactEMail', $customresult); ?></dd>
						</div>
						<div class="key_point_list_div">
							<dt>Clinical Trial ID</dt>
							<dd><?php if(empty($customresult->NCTId)) echo "-"; echo $customresult->NCTId;?></dd>
						</div>
					</dl>
					<hr>
					<dl class="extarnal_link">
						<dt>URL</dt>
						<dd>
							<a href="https://clinicaltrials.gov/ct2/show/record/<?php echo $customresult->NCTId; ?>" target="_blank" rel="noopener noreferrer">https://clinicaltrials.gov/ct2/show/record/<?php echo $customresult->NCTId; ?></a>
						</dd>
					</dl>
				</div>
			</div>
		</div>
		<div class="row">
			<div class="col-12">
			
					<div class="detail_summry_div">
						<h3 id="detail_summry_h3">Key Information</h3>
						<ul>
							<li><?php if($customresult->key_information != ""){ echo $customresult->key_information; }else{ echo "-"; } ?></li>
						</ul> 
					</div>
					<div class="detail_summry_div">
						<h3 id="detail_summry_h3">How the treatment works</h3>
						<ul>
							<li><?php getCustomData('InterventionDescription', 'CustomInterventionDescription', $customresult); ?></li>
							<li>Visit our <a href="https://osteosarcomanow.org/drugs-and-interventions/">drugs and interventions</a> page to find out more about this treatment, including how it works and what it’s used for.</li>
						</ul> 
					</div>
				<?php if(!empty($parsedInclusionCriteria)){ //echo "<pre>"; print_r($parsedInclusionCriteria); echo "</pre>"; ?>
					<div class="detail_summry_div">
						<h3 id="detail_summry_h3">Who is the trial for?</h3>
						<ul>
						<?php foreach($parsedInclusionCriteria as $parsedInclusionCriteriaval){ //if($parsedInclusionCriteriaval == "") echo "hemtest"; ?>
							<li><?php echo $parsedInclusionCriteriaval; ?></li>
						<?php } ?>
						</ul>
					</div>
				<?php } ?>
				<?php if(!empty($parsedExclusionCriteria)){ ?>
					<div class="detail_summry_div">
						<h3 id="detail_summry_h3">Who is the trial not for?</h3>
						<ul>
						<?php foreach($parsedExclusionCriteria as $parsedExclusionCriteriaval){ ?>
							<li><?php echo $parsedExclusionCriteriaval; ?></li>
						<?php } ?>
						</ul>
					</div>
				<?php } ?>
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
		<div class="row">
			<div class="col-12">
				<a href="javascript:void()" class="backtoresult result_submit btn btn-primary" onclick="history.back();">Back to Results Page</a>
				<!-- <a href="/result/" class="backtoresult result_submit btn btn-primary">Back to Results Page</a>-->
			</div>
		</div>
	</div>
	</div>
<?php get_footer(); ?>
