var url = require('url');
var crypto = require('crypto');
var request = require('request');
var async = require('async');
var BufferHelp = require('bufferhelper');
var iconv = require('iconv-lite');
var fs = require('fs');


var cache = {
    ticket: null,
    time: 0
};

function getSignature(config, url, cb) {
    // console.log('start getSignature');
    // 判断内存中是否有缓存
    if (!cache || !cache.ticket) {
        console.log('readCache');
        readFile(config.cache_json_file + '/cache.json', function(str) {
            if (str) {
                console.log(str);
                cache = JSON.parse(str);
            }
            tryGetSignature(config, url, cb);
        });
    }
    else {
        tryGetSignature(config, url, cb);
    }
}

function checkSignature(config) {
    return function(req, res, next) {
        // console.log('checkSignature');
        req.query = url.parse(req.url, true).query;

        if (req.query.getsignature) {
            // console.log('req.query.getsignature');
            return next();
        }


        if (!req.query.signature) {
            return res.end('Access Denied!');
        }
        var tmp = [config.appToken, req.query.timestamp, req.query.nonce].sort().join('');
        var signature = crypto.createHash('sha1').update(tmp).digest('hex');
        if (req.query.signature != signature) {
            console.log('req.query.signature != signature');
            return res.end('Auth failed!'); // 指纹码不匹配时返回错误信息，禁止后面的消息接受及发送
        }
        if (req.query.echostr) {
            // console.log('req.query.echostr');
            return res.end(req.query.echostr); // 添加公众号接口地址时，返回查询字符串echostr表示验证通过
        }
        // 消息真实性验证通过，继续后面的处理
        return next();
    };
}


function getToken(config, cb) {
    var tokenUrl = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appId=' + config.appId + '&secret=' + config.appSecret;

    request.get(tokenUrl, function(error, response, body) {
        if (error) {
            cb('getToken error', error);
        }
        else {

            try {
                var token = JSON.parse(body).access_token;
                cb(null, token);
            }
            catch (e) {
                cb('getToken error', e);
            }
        }
    });
}

function getNewTicket(token, cb) {
    request.get('https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=' + token + '&type=jsapi', function(error, res, body) {
        if (error) {
            cb('getNewTicket error', error);
        }
        else {
            try {
                // console.log(JSON.parse(body));
                var ticket = JSON.parse(body).ticket;
                cb(null, ticket);
            }
            catch (e) {
                cb('getNewTicket error', e);
            }
        }
    });
}



function tryGetSignature(config, u, cb) {
    // 判断cache 是否过期
    if (!cache.ticket || (new Date().getTime() - cache.time) > 7000000) {
        cache.time = cache.time + 10 * 1000;  // 缓解高并发多次获取
        async.waterfall([function(cb) {
            console.log('start getNew Ticket', cache);
            getToken(config, cb);
        }, function(token, cb) {
            getNewTicket(token, cb);
        }], function(error, result) {
            if (error) {
                cb('getToken getNewTicket error', error);
            }
            else {
                cache.ticket = result;
                cache.time = new Date().getTime();
                // 文件保存
                writeFile(config.cache_json_file + '/cache.json', JSON.stringify(cache));
                // console.log(result);

                var timestamp = getTimesTamp();
                var noncestr = getNonceStr();
                var str = 'jsapi_ticket=' + result + '&noncestr='+ noncestr+'&timestamp=' + timestamp + '&url=' + u;
                // console.log(str);
                var signature = crypto.createHash('sha1').update(str).digest('hex');
                cb(null, {
                    appId: config.appId,
                    timestamp: timestamp,
                    nonceStr: noncestr,
                    signature: signature
                });
            }
        });
    }
    else {
        // console.log('缓存获取');
        var timestamp = getTimesTamp();
        var noncestr = getNonceStr();
        var str = 'jsapi_ticket=' + cache.ticket + '&noncestr=' + noncestr + '&timestamp=' + timestamp + '&url=' + u;
        // console.log(str);
        var signature = crypto.createHash('sha1').update(str).digest('hex');
        cb(null, {
            appId: config.appId,
            timestamp: timestamp,
            nonceStr: noncestr,
            signature: signature
        });
    }
}

function getTimesTamp() {
    return parseInt(new Date().getTime() / 1000) + '';
}

function getNonceStr() {
    return Math.random().toString(36).substr(2, 15);
}


function readFile(path, cb) {
    var readstream = fs.createReadStream(path);
    var bf = new BufferHelp();
    readstream.on('data', function(chunk) {
        bf.concat(chunk);
    });
    readstream.on('end', function() {
        cb && cb(decodeBuffer(bf));
    });
}

function writeFile(path, str, cb) {
    var writestream = fs.createWriteStream(path);

    writestream.write(str);
    writestream.on('close', function() {
        cb && cb();
    });
}

function decodeBuffer(bf, encoding) {
    var val = iconv.decode(bf.toBuffer(), encoding || 'utf8');
    if (val.indexOf('�') != -1) {
        val = iconv.decode(bf.toBuffer(), 'gbk');
    }
    return val;
}

exports.checkSignature = checkSignature;

exports.getSignature = function(config) {
    cache_json_file = config.cache_json_file + '/cache.json';
    fs.exists(cache_json_file, function (exists) {
      if(exists === false){
        fs.writeFile(cache_json_file, '{}', function (err) {
          if (err) throw err;
          console.log('cache_json_file is created!');
        });
      }else{
        console.log('cache_json_file is exist!');
      }
    });

    return function(url, cb) {
        getSignature(config, url, cb);
    }
};

/**
 https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appId=wxe65090bdafbc19cf&secret=HAIv98wEFgRCtdV74syeDJpZONqKYjQm

'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=' + token + '&type=jsapi'


https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appId=wx21ccd3e4154404f5&secret=6fa2fbfb306a54375b228e9488f3f0d5

https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=88_3Mph-21wkKR8cn8f7_-8R9sV7POOOE22JUpR8GmU_QD5gmWz_3k3Mql-kIcAA6IJnBzW8EyIZ7JIDUYnU5at2kiW6opcu5sv5wCck0mhGxN5U7bkCchYLukRyL4QGVdAHAUKZ&type=jsapi
 */