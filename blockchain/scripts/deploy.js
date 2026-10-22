const hre = require("hardhat");

async function main() {
  const BatchCommit = await hre.ethers.getContractFactory("BatchCommit");

  const contract = await BatchCommit.deploy();

  await contract.waitForDeployment();  

  const address = await contract.getAddress();

  console.log(" Deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
