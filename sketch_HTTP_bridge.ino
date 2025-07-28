/*TODO: funzionamento sensore di rumore (array di valori)*/

#include "DHT.h"
#include <math.h>
#include "MQ135.h"

#define DHTPIN 6
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

//handle time
unsigned long timestamp;
unsigned long millisCurrent;
unsigned long millisLast = 0;

//button on pin 4
//led on pin 12
const int BUTTON_PIN = 4;
const int BUZZER_PIN = 11;
const int Y_LED_PIN    = 5;
const int R_LED_PIN    = 12;
const int G_LED_PIN    = 3;
const int soundSensor = 10;

int lightSensorPin = A4;
int qualityPin = A0;

//variables
int y_ledState = LOW;
int r_ledState = LOW;
int g_ledState = LOW;
int buzzerState = LOW;
int lastButtonState;
int currentButtonState;

int lightData = 0;
int qualityData;
float humidity;
float temperature;

//for sound sensor
unsigned long count = 0;
unsigned long sumSound = 0;
int averageSound;
const int SAMPLE_TIME = 100;
int sampleBufferValue = 0;

//for people counter
const int IRsensor1 = 8;
const int IRsensor2 = 9;
String sequence = "";
int currentPeople = 0;
int timeoutCounter = 0;

bool alarmActive = false;
bool stateAlarm = false;
unsigned long alarmPreviousMillis = 0;
const long alarmInterval = 500; // tempo ON/OFF in ms

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);

  timestamp = millis();

  pinMode(BUTTON_PIN, INPUT);
  pinMode(lightSensorPin, INPUT);
  pinMode(qualityPin, INPUT);
  pinMode(soundSensor, INPUT);
  pinMode(IRsensor1, INPUT);
  pinMode(IRsensor2, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(R_LED_PIN,OUTPUT);
  pinMode(Y_LED_PIN,OUTPUT);
  pinMode(G_LED_PIN, OUTPUT);
  dht.begin();

  currentButtonState = digitalRead(BUTTON_PIN);
}

void loop() {
  // put your main code here, to run repeatedly:
  millisCurrent = millis();

  lastButtonState = currentButtonState;
  currentButtonState = digitalRead(BUTTON_PIN);

  if(lastButtonState == HIGH && currentButtonState == LOW) {

    y_ledState = !y_ledState;

    digitalWrite(Y_LED_PIN, y_ledState);
  }


  if (Serial.available()) { 
    int data = Serial.read();
    
    if (data == 'F') {
      r_ledState = LOW;
      buzzerState = LOW;
      alarmActive = false;  // turn off alarm mode
    }
    
    if (data == 'O') {
      alarmActive = true;  // activate intermittent alarm mode
    }

    // If it is not in alarm mode, set the pins normally
    if (!alarmActive) {
      digitalWrite(R_LED_PIN, r_ledState);
      noTone(BUZZER_PIN);
    }

    if(data == 'L'){
      digitalWrite(Y_LED_PIN, LOW);
    }
    if(data == 'H'){
      digitalWrite(Y_LED_PIN, HIGH);
    }

    if(data == 'P'){
      digitalWrite(G_LED_PIN, HIGH);
    }
    if(data == 'S'){
      digitalWrite(G_LED_PIN, LOW);
      r_ledState = LOW;
      buzzerState = LOW;
      alarmActive = false;  // turn off alarm mode
    }
  }


  //for sound in a room
  if(digitalRead(soundSensor) == LOW) {
    sampleBufferValue++;
  }

  qualityData = analogRead(qualityPin);

  if(millisCurrent - millisLast > SAMPLE_TIME){
    sumSound += sampleBufferValue;
    count = count + 1;
    sampleBufferValue = 0;
    millisLast = millisCurrent;
  }
  
  //for bidirectional counter
  if(!digitalRead(IRsensor1)){
    sequence += "1";
  }else if(!digitalRead(IRsensor2)){
    sequence += "2";
  }

  if(sequence.equals("12")){
    currentPeople++;  
    sequence="";
    delay(100);
  }else if(sequence.equals("21") && currentPeople > 0){
    currentPeople--;  
    sequence="";
    delay(100);
  }

  if(sequence.length() > 2 || sequence.equals("11") || sequence.equals("22") || timeoutCounter > 200){
    sequence="";  
  }

  if(sequence.length() == 1){ //
    timeoutCounter++;
  }else{
    timeoutCounter=0;
  }

  if (alarmActive) {
    unsigned long currentMillis = millis();
    if (currentMillis - alarmPreviousMillis >= alarmInterval) {
      alarmPreviousMillis = currentMillis;
      stateAlarm = !stateAlarm;

      if (stateAlarm) {
        tone(BUZZER_PIN, 1000);
        digitalWrite(R_LED_PIN, HIGH);
      } else {
        noTone(BUZZER_PIN);
        digitalWrite(R_LED_PIN, LOW);
      }
    }
  }


  //write data on server
  unsigned char dataLight;
  if (millis() - timestamp > 60000){
    // light in a room
    if(y_ledState == LOW) {
      dataLight = 0 & 0x00FF;
    }
    else{
      dataLight = 1 & 0x00FF;
    }

    lightData = analogRead(lightSensorPin);
    humidity = dht.readHumidity();
    temperature = dht.readTemperature();

    averageSound = sumSound / count;
    if(averageSound == 0){
      averageSound = 1;
    }

    /*Serial.print("--------------------------------- ");
    Serial.print(sumSound);
    Serial.print(" - ");
    Serial.print(count);
    Serial.print(" : ");
    Serial.println(averageSound);*/

    // data packet
    // FF  nPacchetti  dato1 FE
    /*Serial.write(0xFF);

    Serial.write(0x07);

    Serial.write(dataLight);
    Serial.write((char)(map(lightData, 0, 1023, 0, 253)));
    Serial.write((char)(map(qualityData, 0, 1023, 0, 253)));
    Serial.write((char)(map(round(temperature), 0, 1023, 0, 253)));
    Serial.write((char)(map(round(humidity), 0, 1023, 0, 253)));
    Serial.write((char)(map(averageSound, 0, 1023, 0, 253)));
    Serial.write((char)(map(currentPeople, 0, 1023, 0, 253)));
  
    Serial.write(0xFE);*/

    Serial.print("{ 'bridge_name': ");
    Serial.print("'casa_tua'");
    Serial.print(", 'room_name': ");
    Serial.print("'simB'");
    Serial.print(", 'temperature': ");
    Serial.print(round(temperature));
    //Serial.print(40);
    Serial.print(", 'humidity': ");
    Serial.print(round(humidity));
    Serial.print(", 'light': ");
    Serial.print(lightData); //light sensor
    Serial.print(", 'co2': ");
    Serial.print(qualityData);
    Serial.print(", 'sound': ");
    Serial.print(averageSound);
    //Serial.print(20);
    Serial.print(", 'people': ");
    Serial.print(currentPeople);
    Serial.print(", 'room_size': ");
    Serial.print(4);
    Serial.print(", 'latitudine': ");
    Serial.print(44.6568);
    Serial.print(", 'longitudine': ");
    Serial.print(10.9202);
    Serial.print(", 'price': ");
    Serial.print(0);
    Serial.print(", 'type': ");
    Serial.print("'studio'");
    /*Serial.print(", 'Light': "); //artificial light (0/1)
    Serial.print(dataLight);*/    
    
    Serial.println("}");
    
    timestamp = millis();
    count = 0;
    sumSound = 0;
  }
}