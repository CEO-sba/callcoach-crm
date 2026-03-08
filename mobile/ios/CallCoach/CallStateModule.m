#import <React/RCTBridgeModule.h>
#import <React/RCTEventEmitter.h>
#import <CallKit/CallKit.h>
#import <CoreTelephony/CTCallCenter.h>
#import <CoreTelephony/CTCall.h>

@interface CallStateModule : RCTEventEmitter <RCTBridgeModule, CXCallObserverDelegate>

@property (nonatomic, strong) CXCallObserver *callObserver;
@property (nonatomic, copy) NSString *lastState;
@property (nonatomic, assign) BOOL isListening;

@end

@implementation CallStateModule

RCT_EXPORT_MODULE();

- (instancetype)init
{
  self = [super init];
  if (self) {
    _callObserver = [[CXCallObserver alloc] init];
    _lastState = @"";
    _isListening = NO;
  }
  return self;
}

+ (BOOL)requiresMainQueueSetup
{
  return NO;
}

- (NSArray<NSString *> *)supportedEvents
{
  return @[@"onCallStateChanged"];
}

RCT_EXPORT_METHOD(startListening)
{
  if (self.isListening) return;

  [self.callObserver setDelegate:self queue:dispatch_get_main_queue()];
  self.isListening = YES;
}

RCT_EXPORT_METHOD(stopListening)
{
  if (!self.isListening) return;

  // CXCallObserver doesn't have a removeDelegate method,
  // but setting a nil delegate-like behavior by flagging
  self.isListening = NO;
  self.lastState = @"";
}

RCT_EXPORT_METHOD(addListener:(NSString *)eventName)
{
  // No-op: required for RN NativeEventEmitter
}

RCT_EXPORT_METHOD(removeListeners:(NSInteger)count)
{
  // No-op: required for RN NativeEventEmitter
}

#pragma mark - CXCallObserverDelegate

- (void)callObserver:(CXCallObserver *)callObserver callChanged:(CXCall *)call
{
  if (!self.isListening) return;

  NSString *eventState;

  if (call.hasEnded) {
    eventState = @"callEnded";
  } else if (call.hasConnected) {
    eventState = @"callConnected";
  } else if (!call.isOutgoing && !call.hasConnected && !call.hasEnded) {
    eventState = @"callRinging";
  } else if (call.isOutgoing && !call.hasConnected) {
    eventState = @"callConnected"; // Outgoing call dialing
  } else {
    return;
  }

  // Avoid duplicate events
  if ([eventState isEqualToString:self.lastState]) return;
  self.lastState = eventState;

  [self sendEventWithName:@"onCallStateChanged"
                     body:@{
                       @"state": eventState,
                       @"number": [NSNull null] // iOS doesn't expose phone numbers via CallKit
                     }];
}

@end
