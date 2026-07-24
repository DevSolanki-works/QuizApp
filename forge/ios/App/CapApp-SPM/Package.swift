// swift-tools-version: 5.9
import PackageDescription

// DO NOT MODIFY THIS FILE - managed by Capacitor CLI commands
let package = Package(
    name: "CapApp-SPM",
    platforms: [.iOS(.v15)],
    products: [
        .library(
            name: "CapApp-SPM",
            targets: ["CapApp-SPM"])
    ],
    dependencies: [
        .package(url: "https://github.com/ionic-team/capacitor-swift-pm.git", exact: "8.4.2"),
        .package(name: "CapacitorCommunityAdmob", path: "../../../node_modules/@capacitor-community/admob"),
        .package(name: "CapacitorFirebaseAnalytics", path: "../../../node_modules/@capacitor-firebase/analytics"),
        .package(name: "CapacitorFirebaseMessaging", path: "../../../node_modules/@capacitor-firebase/messaging"),
        .package(name: "CapacitorBrowser", path: "../../../node_modules/@capacitor/browser"),
        .package(name: "CapacitorLocalNotifications", path: "../../../node_modules/@capacitor/local-notifications"),
        .package(name: "CapawesomeCapacitorAppUpdate", path: "../../../node_modules/@capawesome/capacitor-app-update"),
        .package(name: "CapawesomeCapacitorGoogleSignIn", path: "../../../node_modules/@capawesome/capacitor-google-sign-in")
    ],
    targets: [
        .target(
            name: "CapApp-SPM",
            dependencies: [
                .product(name: "Capacitor", package: "capacitor-swift-pm"),
                .product(name: "Cordova", package: "capacitor-swift-pm"),
                .product(name: "CapacitorCommunityAdmob", package: "CapacitorCommunityAdmob"),
                .product(name: "CapacitorFirebaseAnalytics", package: "CapacitorFirebaseAnalytics"),
                .product(name: "CapacitorFirebaseMessaging", package: "CapacitorFirebaseMessaging"),
                .product(name: "CapacitorBrowser", package: "CapacitorBrowser"),
                .product(name: "CapacitorLocalNotifications", package: "CapacitorLocalNotifications"),
                .product(name: "CapawesomeCapacitorAppUpdate", package: "CapawesomeCapacitorAppUpdate"),
                .product(name: "CapawesomeCapacitorGoogleSignIn", package: "CapawesomeCapacitorGoogleSignIn")
            ]
        )
    ]
)
