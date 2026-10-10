package org.hackphs.ball_drone

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "ball_drone/settings")
            .setMethodCallHandler { call, result ->
                if (call.method == "openAppSettings") {
                    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                    intent.data = Uri.parse("package:" + packageName)
                    startActivity(intent)
                    result.success(null)
                } else {
                    result.notImplemented()
                }
            }
    }
}
