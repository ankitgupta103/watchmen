export const AWS_IOT_CONFIG = {
  region: process.env.NEXT_PUBLIC_AWS_REGION,
  endpoint: process.env.NEXT_PUBLIC_AWS_IOT_ENDPOINT,
  identityPoolId: process.env.NEXT_PUBLIC_AWS_IOT_IDENTITY_POOL_ID,
  amplifyConfig: {
    Auth: {
      Cognito: {
        identityPoolId: process.env.NEXT_PUBLIC_AWS_COGNITO_IDENTITY_POOL_ID,
        allowGuestAccess: true,
      },
    },
    region: process.env.NEXT_PUBLIC_AWS_REGION,
  },
};
