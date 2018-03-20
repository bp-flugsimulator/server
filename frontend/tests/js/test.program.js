import { Selector } from 'testcafe';

fixture `program tests`
	.page `http://localhost:8000/slaves`
	.beforeEach(async t => {
		let submit = slaveForm.find('.submit-btn');	
		await t
		.click('.slave-action-add')
		.typeText(nameField, 'Testnode2')
		.typeText(ipAddress, '192.168.178.2')
		.typeText(macAddress, '00:00:00:00:00:13')
		.click(submit)
	})
	.afterEach(async t => {
	await t
		.click('.slave-action-delete')
		.click('#deleteSlaveModalButton')
});


const slaveForm = Selector('#slaveForm');
const nameField = slaveForm.find('#id_name');
const ipAddress = slaveForm.find('#id_ip_address')
const macAddress = slaveForm.find('#id_mac_address');
const submitButton = slaveForm.find('.btn-info');

test('create program', async t => {
	let programForm = Selector('#programForm');
	let programField = programForm.find('#id_name');
	let programArguments = programForm.find('#id_arguments');
	let programPath = programForm.find('#id_path');
	let programlist = Selector('#slave');
	let testProgram = programlist.find('li').find('a').withText('Testprogram');
	let submitProgramForm = programForm.find('.submit-btn')
	await t
	.click('.program-action-add')
	.typeText(programField, 'Testprogram')
	.typeText(programArguments, 'quiet')
	.typeText(programPath, 'testPath')
	.click(submitProgramForm)
	//.expect(testProgram.exists).ok()
});

