import{fromIni}from'@aws-sdk/credential-providers';
// In AWS the SDK uses the instance role; developer credentials stay on the Mac.
export const awsCredentials=process.env.AWS_CREDENTIAL_MODE==='instance'?{}:{credentials:fromIni({profile:process.env.AWS_PROFILE||'default'})};
